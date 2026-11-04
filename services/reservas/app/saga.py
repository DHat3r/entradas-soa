"""Coordinación de la compra. Los estados y eventos están en docs/arquitectura.md.

Regla de esta saga: cada transición es un UPDATE condicionado al estado esperado y el evento
se publica ANTES del commit.
- Si publicar falla, la transacción se revierte y RabbitMQ reintenta el mensaje entrante.
- Si la respuesta llega antes del commit, su UPDATE espera el bloqueo de la fila y luego ve el
  estado nuevo, así que no se pierde.
- Si el mensaje entrante está repetido, el UPDATE no afecta filas y no se hace nada.
"""

import asyncio
import logging
import uuid
from datetime import UTC, datetime, timedelta
from typing import Literal

from basedatos import Sesiones
from mensajeria import ErrorDeNegocio, SinRespuesta, exigir_rol
from pydantic import BaseModel, Field
from sqlalchemy import select, update
from sqlalchemy.ext.asyncio import AsyncSession

from app.modelos import Reserva

PLAZO_DE_PAGO = timedelta(minutes=10)
TIEMPO_PARA_APARTAR_SEGUNDOS = 3.0  # Menos que los 5 s que espera el gateway.
INTERVALO_VENCIMIENTO_SEGUNDOS = 15
LOTE_VENCIMIENTO = 100

log = logging.getLogger("reservas")


class ReservaNueva(BaseModel):
    sector_id: uuid.UUID
    cantidad: int = Field(ge=1, le=6)


class ReservaPorId(BaseModel):
    reserva_id: uuid.UUID


class PedidoDePago(ReservaPorId):
    resultado_simulado: Literal["aprobar", "rechazar"]


class ResultadoDePago(BaseModel):
    reserva_id: uuid.UUID


def a_dict(reserva: Reserva) -> dict:
    return {
        "id": str(reserva.id),
        "estado": reserva.estado,
        "cantidad": reserva.cantidad,
        "monto_clp": reserva.monto_clp,
        "evento_id": str(reserva.evento_id) if reserva.evento_id else None,
        "evento_nombre": reserva.evento_nombre,
        "sector_nombre": reserva.sector_nombre,
        "vence_en": reserva.vence_en.isoformat(),
    }


async def _cancelacion(bus, reserva: Reserva, motivo: str) -> None:
    await bus.publicar(
        "reserva.cancelada",
        {"reserva_id": str(reserva.id), "sector_id": str(reserva.sector_id), "motivo": motivo},
    )


async def _transicion(sesion: AsyncSession, reserva_id, desde: str, hacia: str, **cambios):
    """Cambia de estado solo si sigue en el esperado. Devuelve la reserva o None si no aplicó."""
    return await sesion.scalar(
        update(Reserva)
        .where(Reserva.id == reserva_id, Reserva.estado == desde)
        .values(estado=hacia, **cambios)
        .returning(Reserva)
    )


async def vencer_reservas(bus, sesiones: Sesiones) -> int:
    """Libera las reservas cuyo plazo pasó. Devuelve cuántas venció."""
    async with sesiones() as sesion:
        # SKIP LOCKED: si otra transacción tiene la fila (por ejemplo, un pago), no la espera.
        vencidas = (
            await sesion.scalars(
                select(Reserva)
                .where(
                    Reserva.estado.in_(("CREADA", "PENDIENTE_PAGO")),
                    Reserva.vence_en <= datetime.now(UTC),
                )
                .limit(LOTE_VENCIMIENTO)
                .with_for_update(skip_locked=True)
            )
        ).all()
        for reserva in vencidas:
            # Una reserva CREADA vencida significa que el servicio cayó mientras apartaba.
            sin_apartar = reserva.estado == "CREADA"
            reserva.estado = "CANCELADA" if sin_apartar else "VENCIDA"
            await _cancelacion(bus, reserva, "error" if sin_apartar else "vencida")
        await sesion.commit()
    return len(vencidas)


async def tarea_de_vencimiento(bus, sesiones: Sesiones) -> None:
    while True:
        try:
            await vencer_reservas(bus, sesiones)
        except Exception:
            # Se reintenta en la siguiente vuelta: un fallo puntual no debe detener la tarea.
            log.exception("Error al vencer reservas")
        await asyncio.sleep(INTERVALO_VENCIMIENTO_SEGUNDOS)


def registrar_saga(bus, sesiones: Sesiones) -> None:
    @bus.accion("crear")
    async def crear(datos: dict, identidad) -> dict:
        exigir_rol(identidad, "cliente")
        nueva = ReservaNueva(**datos)
        # Se guarda antes de pedir cupos: si este servicio cae a la mitad, queda un rastro
        # que el vencimiento puede compensar.
        reserva = Reserva(
            id=uuid.uuid4(),
            cliente_id=uuid.UUID(identidad["usuario_id"]),
            cliente_correo=identidad["correo"],
            sector_id=nueva.sector_id,
            cantidad=nueva.cantidad,
            estado="CREADA",
            vence_en=datetime.now(UTC) + PLAZO_DE_PAGO,
        )
        async with sesiones() as sesion:
            sesion.add(reserva)
            await sesion.commit()

        pedido = {
            "reserva_id": str(reserva.id),
            "sector_id": str(reserva.sector_id),
            "cantidad": reserva.cantidad,
        }
        try:
            cupos = await bus.pedir(
                "eventos", "apartar_cupos", pedido, tiempo=TIEMPO_PARA_APARTAR_SEGUNDOS
            )
        except ErrorDeNegocio:
            # eventos revirtió su transacción: no hay nada que liberar.
            async with sesiones() as sesion:
                await _transicion(sesion, reserva.id, "CREADA", "CANCELADA")
                await sesion.commit()
            raise
        except SinRespuesta as error:
            # No se sabe si alcanzó a apartar, así que se compensa de todos modos.
            async with sesiones() as sesion:
                if await _transicion(sesion, reserva.id, "CREADA", "CANCELADA"):
                    await _cancelacion(bus, reserva, "error")
                await sesion.commit()
            raise ErrorDeNegocio(
                "no_disponible", "No pudimos apartar tus entradas, intenta de nuevo"
            ) from error

        async with sesiones() as sesion:
            # El monto lo calcula el servidor con el precio de eventos, nunca el cliente.
            confirmada = await _transicion(
                sesion,
                reserva.id,
                "CREADA",
                "PENDIENTE_PAGO",
                evento_id=uuid.UUID(cupos["evento_id"]),
                evento_nombre=cupos["evento_nombre"],
                sector_nombre=cupos["sector_nombre"],
                monto_clp=cupos["precio_clp"] * reserva.cantidad,
                vence_en=datetime.now(UTC) + PLAZO_DE_PAGO,
            )
            await sesion.commit()
        if confirmada is None:
            raise ErrorDeNegocio("conflicto", "La reserva ya no está disponible")
        return a_dict(confirmada)

    @bus.accion("pagar")
    async def pagar(datos: dict, identidad) -> dict:
        exigir_rol(identidad, "cliente")
        pedido = PedidoDePago(**datos)
        cliente_id = uuid.UUID(identidad["usuario_id"])
        async with sesiones() as sesion:
            # La condición de vence_en resuelve la carrera entre pagar y vencer.
            reserva = await sesion.scalar(
                update(Reserva)
                .where(
                    Reserva.id == pedido.reserva_id,
                    Reserva.cliente_id == cliente_id,
                    Reserva.estado == "PENDIENTE_PAGO",
                    Reserva.vence_en > datetime.now(UTC),
                )
                .values(estado="PAGANDO")
                .returning(Reserva)
            )
            if reserva is None:
                actual = await sesion.get(Reserva, pedido.reserva_id)
                if actual is None or actual.cliente_id != cliente_id:
                    raise ErrorDeNegocio("no_encontrado", "Reserva no encontrada")
                raise ErrorDeNegocio("conflicto", "Esta reserva ya no se puede pagar")
            await bus.publicar(
                "pago.solicitado",
                {
                    "reserva_id": str(reserva.id),
                    "monto_clp": reserva.monto_clp,
                    "resultado_simulado": pedido.resultado_simulado,
                },
            )
            await sesion.commit()
        return a_dict(reserva)

    @bus.accion("detalle")
    async def detalle(datos: dict, identidad) -> dict:
        exigir_rol(identidad, "cliente")
        pedido = ReservaPorId(**datos)
        async with sesiones() as sesion:
            reserva = await sesion.get(Reserva, pedido.reserva_id)
        # Si es ajena, responde igual que si no existiera.
        if reserva is None or str(reserva.cliente_id) != identidad["usuario_id"]:
            raise ErrorDeNegocio("no_encontrado", "Reserva no encontrada")
        return a_dict(reserva)

    @bus.accion("listar_mias")
    async def listar_mias(datos: dict, identidad) -> list[dict]:
        exigir_rol(identidad, "cliente")
        async with sesiones() as sesion:
            reservas = (
                await sesion.scalars(
                    select(Reserva)
                    .where(Reserva.cliente_id == uuid.UUID(identidad["usuario_id"]))
                    .order_by(Reserva.creada_en.desc())
                )
            ).all()
        return [a_dict(reserva) for reserva in reservas]

    @bus.al_recibir("pago.aprobado")
    async def al_aprobar_pago(datos: dict) -> None:
        resultado = ResultadoDePago.model_validate(datos)
        async with sesiones() as sesion:
            reserva = await _transicion(sesion, resultado.reserva_id, "PAGANDO", "CONFIRMADA")
            if reserva:
                await bus.publicar(
                    "reserva.confirmada",
                    {
                        "reserva_id": str(reserva.id),
                        "cliente_id": str(reserva.cliente_id),
                        "cliente_correo": reserva.cliente_correo,
                        "evento_id": str(reserva.evento_id),
                        "evento_nombre": reserva.evento_nombre,
                        "sector_nombre": reserva.sector_nombre,
                        "cantidad": reserva.cantidad,
                    },
                )
            await sesion.commit()

    @bus.al_recibir("pago.rechazado")
    async def al_rechazar_pago(datos: dict) -> None:
        resultado = ResultadoDePago.model_validate(datos)
        async with sesiones() as sesion:
            reserva = await _transicion(sesion, resultado.reserva_id, "PAGANDO", "RECHAZADA")
            if reserva:
                await _cancelacion(bus, reserva, "rechazada")
            await sesion.commit()
