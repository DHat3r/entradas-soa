import uuid
from datetime import UTC, datetime

from basedatos import Sesiones
from mensajeria import ErrorDeNegocio, exigir_rol
from pydantic import BaseModel, Field
from sqlalchemy import select, update
from sqlalchemy.dialects.postgresql import insert

from app.codigos import generar_codigo, leer_codigo, qr_como_data_uri
from app.modelos import Entrada


class ReservaConfirmada(BaseModel):
    reserva_id: uuid.UUID
    cliente_id: uuid.UUID
    cliente_correo: str
    evento_id: uuid.UUID
    evento_nombre: str
    sector_nombre: str
    cantidad: int = Field(ge=1, le=6)


class PedidoDeValidacion(BaseModel):
    codigo: str = Field(min_length=1, max_length=200)


def _a_dict(entrada: Entrada) -> dict:
    return {
        "id": str(entrada.id),
        "evento_nombre": entrada.evento_nombre,
        "sector_nombre": entrada.sector_nombre,
        "numero": entrada.numero,
        "usada_en": entrada.usada_en.isoformat() if entrada.usada_en else None,
    }


def registrar_acciones(bus, sesiones: Sesiones, qr_secret: str) -> None:
    @bus.al_recibir("reserva.confirmada")
    async def al_confirmar_reserva(datos: dict) -> None:
        reserva = ReservaConfirmada.model_validate(datos, extra="ignore")
        filas = [
            {
                "id": uuid.uuid4(),
                "reserva_id": reserva.reserva_id,
                "numero": numero,
                "cliente_id": reserva.cliente_id,
                "cliente_correo": reserva.cliente_correo,
                "evento_id": reserva.evento_id,
                "evento_nombre": reserva.evento_nombre,
                "sector_nombre": reserva.sector_nombre,
            }
            for numero in range(1, reserva.cantidad + 1)
        ]
        async with sesiones() as sesion:
            await sesion.execute(insert(Entrada).values(filas).on_conflict_do_nothing())
            # Se leen de vuelta: en una reentrega, los id válidos son los que ya estaban guardados.
            entradas = (
                await sesion.scalars(
                    select(Entrada)
                    .where(Entrada.reserva_id == reserva.reserva_id)
                    .order_by(Entrada.numero)
                )
            ).all()
            await bus.publicar(
                "entradas.emitidas",
                {
                    "reserva_id": str(reserva.reserva_id),
                    "cliente_correo": reserva.cliente_correo,
                    "evento_nombre": reserva.evento_nombre,
                    "sector_nombre": reserva.sector_nombre,
                    "entradas": [
                        {"id": str(e.id), "codigo": generar_codigo(e.id, qr_secret)}
                        for e in entradas
                    ],
                },
            )
            await sesion.commit()

    @bus.accion("listar_mias")
    async def listar_mias(datos: dict, identidad) -> list[dict]:
        exigir_rol(identidad, "cliente")
        async with sesiones() as sesion:
            entradas = (
                await sesion.scalars(
                    select(Entrada)
                    .where(Entrada.cliente_id == uuid.UUID(identidad["usuario_id"]))
                    .order_by(Entrada.emitida_en.desc(), Entrada.numero)
                )
            ).all()
        return [
            {**_a_dict(e), "qr": qr_como_data_uri(generar_codigo(e.id, qr_secret))}
            for e in entradas
        ]

    @bus.accion("validar")
    async def validar(datos: dict, identidad) -> dict:
        exigir_rol(identidad, "organizador", "validador")
        pedido = PedidoDeValidacion(**datos)
        entrada_id = leer_codigo(pedido.codigo.strip(), qr_secret)
        if entrada_id is None:
            return {"resultado": "invalida", "mensaje": "Código inválido"}
        async with sesiones() as sesion:
            # Atómico: si dos personas escanean el mismo QR a la vez, solo una puede ganar.
            usada = await sesion.scalar(
                update(Entrada)
                .where(Entrada.id == entrada_id, Entrada.usada_en.is_(None))
                .values(usada_en=datetime.now(UTC))
                .returning(Entrada)
            )
            await sesion.commit()
            if usada:
                return {"resultado": "valida", "mensaje": "Puede entrar", "entrada": _a_dict(usada)}
            existente = await sesion.get(Entrada, entrada_id)
        if existente is None:
            raise ErrorDeNegocio("no_encontrado", "Entrada no encontrada")
        return {
            "resultado": "ya_usada",
            "mensaje": "Esta entrada ya se usó",
            "entrada": _a_dict(existente),
        }
