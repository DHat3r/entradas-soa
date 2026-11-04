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
            if await sesion.get(CorreoEnviado, entradas.reserva_id):
                return
            # Se registra después de enviar: es preferible un correo duplicado en un caso muy raro
            # antes que una entrada que nunca llega. Si el envío falla, la excepción sube, no se
            # guarda la fila y RabbitMQ reintenta.
            await enviador.enviar(construir_correo(remitente, entradas))
            await sesion.execute(
                insert(CorreoEnviado)
                .values(reserva_id=entradas.reserva_id, destinatario=entradas.cliente_correo)
                .on_conflict_do_nothing()
            )
            await sesion.commit()
