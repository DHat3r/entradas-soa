"""Procesa los pedidos de pago. Cada reserva tiene como máximo un pago guardado.

Regla de este procesador: el pago se guarda y el resultado se publica ANTES del commit.
- Si publicar falla, la transacción se revierte y RabbitMQ reintenta el mensaje.
- Es seguro repetir: si el pago ya existía, no se guarda otro y se publica el estado que
  quedó guardado. Reservas ignora los resultados repetidos.
"""

import uuid
from typing import Literal

from basedatos import Sesiones
from pydantic import BaseModel, Field
from sqlalchemy import select
from sqlalchemy.dialects.postgresql import insert

from app.modelos import Pago


class PedidoDePago(BaseModel):
    reserva_id: uuid.UUID
    monto_clp: int = Field(ge=0)
    resultado_simulado: Literal["aprobar", "rechazar"]


def registrar_procesador(bus, sesiones: Sesiones) -> None:
    @bus.al_recibir("pago.solicitado")
    async def al_solicitar_pago(datos: dict) -> None:
        pedido = PedidoDePago.model_validate(datos)
        estado = "APROBADO" if pedido.resultado_simulado == "aprobar" else "RECHAZADO"
        async with sesiones() as sesion:
            await sesion.execute(
                insert(Pago)
                .values(reserva_id=pedido.reserva_id, monto_clp=pedido.monto_clp, estado=estado)
                .on_conflict_do_nothing(index_elements=["reserva_id"])
            )
            pago = await sesion.scalar(select(Pago).where(Pago.reserva_id == pedido.reserva_id))
            await bus.publicar(
                "pago.aprobado" if pago.estado == "APROBADO" else "pago.rechazado",
                {"reserva_id": str(pedido.reserva_id), "pago_id": str(pago.id)},
            )
            await sesion.commit()
