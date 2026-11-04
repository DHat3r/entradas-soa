"""Envía el correo de las entradas cuando llega entradas.emitidas."""

from basedatos import Sesiones
from sqlalchemy.dialects.postgresql import insert

from app.correo import DatosDeEntradas, construir_correo
from app.modelos import CorreoEnviado


def registrar_notificador(bus, sesiones: Sesiones, enviador, remitente: str) -> None:
    @bus.al_recibir("entradas.emitidas")
    async def al_emitir_entradas(datos: dict) -> None:
        entradas = DatosDeEntradas.model_validate(datos)
        async with sesiones() as sesion:
            # Se registra antes de enviar y en la misma transacción. Una copia simultánea espera
            # este commit y luego no inserta nada, así que no reenvía. Si el envío falla, la
            # transacción se revierte y el reintento vuelve a intentarlo.
            nuevo = await sesion.execute(
                insert(CorreoEnviado)
                .values(reserva_id=entradas.reserva_id, destinatario=entradas.cliente_correo)
                .on_conflict_do_nothing()
            )
            if nuevo.rowcount == 0:
                return
            await enviador.enviar(construir_correo(remitente, entradas))
            await sesion.commit()
