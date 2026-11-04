"""Apartar y liberar cupos: la regla de no sobrevender vive aquí."""

import uuid
from datetime import UTC, datetime

from basedatos import Sesiones
from mensajeria import ErrorDeNegocio
from pydantic import BaseModel, Field
from sqlalchemy import select, update
from sqlalchemy.dialects.postgresql import insert

from app.modelos import Apartado, Evento, Sector


class PedidoDeCupos(BaseModel):
    reserva_id: uuid.UUID
    sector_id: uuid.UUID
    cantidad: int = Field(ge=1, le=6)


class ReservaCancelada(BaseModel):
    reserva_id: uuid.UUID
    sector_id: uuid.UUID


def registrar_cupos(bus, sesiones: Sesiones) -> None:
    @bus.accion("apartar_cupos")
    async def apartar_cupos(datos: dict, identidad) -> dict:
        pedido = PedidoDeCupos(**datos)
        async with sesiones() as sesion:
            fila = (
                await sesion.execute(
                    select(Sector, Evento)
                    .join(Evento, Sector.evento_id == Evento.id)
                    .where(Sector.id == pedido.sector_id, Evento.estado == "PUBLICADO")
                )
            ).first()
            if fila is None:
                raise ErrorDeNegocio("no_encontrado", "Sector no encontrado")
            sector, evento = fila
            if evento.fecha <= datetime.now(UTC):
                raise ErrorDeNegocio("conflicto", "El evento ya pasó")
            respuesta = {
                "evento_id": str(evento.id),
                "evento_nombre": evento.nombre,
                "sector_nombre": sector.nombre,
                "precio_clp": sector.precio_clp,
            }

            # Si el apartado ya existe es un reintento: no se descuenta de nuevo.
            nuevo = await sesion.execute(
                insert(Apartado)
                .values(
                    reserva_id=pedido.reserva_id,
                    sector_id=pedido.sector_id,
                    cantidad=pedido.cantidad,
                    liberado=False,
                )
                .on_conflict_do_nothing()
            )
            if nuevo.rowcount == 0:
                apartado = await sesion.get(Apartado, pedido.reserva_id)
                if apartado.liberado:
                    raise ErrorDeNegocio("conflicto", "La reserva ya fue cancelada")
                return respuesta

            # Atómico: PostgreSQL bloquea la fila y vuelve a evaluar el WHERE. Leer y luego
            # escribir dejaría que dos compras simultáneas vieran el mismo cupo libre.
            descuento = await sesion.execute(
                update(Sector)
                .where(Sector.id == pedido.sector_id, Sector.disponibles >= pedido.cantidad)
                .values(disponibles=Sector.disponibles - pedido.cantidad)
            )
            if descuento.rowcount == 0:
                # Al salir sin commit se revierte también el apartado recién insertado.
                raise ErrorDeNegocio("conflicto", "No quedan cupos suficientes en este sector")
            await sesion.commit()
        return respuesta

    @bus.al_recibir("reserva.cancelada")
    async def al_cancelar_reserva(datos: dict) -> None:
        cancelada = ReservaCancelada.model_validate(datos)
        async with sesiones() as sesion:
            # Si aún no hay apartado, deja una marca: un apartar_cupos atrasado encontrará la
            # reserva cancelada y no tomará cupos que nadie liberaría después.
            marca = await sesion.execute(
                insert(Apartado)
                .values(
                    reserva_id=cancelada.reserva_id,
                    sector_id=cancelada.sector_id,
                    cantidad=0,
                    liberado=True,
                )
                .on_conflict_do_nothing()
            )
            if marca.rowcount == 0:
                # Solo una entrega logra pasar liberado de falso a verdadero.
                liberacion = await sesion.execute(
                    update(Apartado)
                    .where(
                        Apartado.reserva_id == cancelada.reserva_id, Apartado.liberado.is_(False)
                    )
                    .values(liberado=True)
                    .returning(Apartado.sector_id, Apartado.cantidad)
                )
                liberado = liberacion.first()
                if liberado:
                    await sesion.execute(
                        update(Sector)
                        .where(Sector.id == liberado.sector_id)
                        .values(disponibles=Sector.disponibles + liberado.cantidad)
                    )
            await sesion.commit()
