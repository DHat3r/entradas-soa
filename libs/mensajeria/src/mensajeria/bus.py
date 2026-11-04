"""Bus sobre RabbitMQ: pedir-responder entre servicios y publicación de eventos."""

import asyncio
import json
import logging
import signal
import uuid
from collections.abc import Awaitable, Callable
from datetime import UTC, datetime
from typing import Any

import aio_pika
from aio_pika.abc import AbstractIncomingMessage
from pydantic import ValidationError

from mensajeria.errores import ErrorDeNegocio, SinRespuesta

EXCHANGE_EVENTOS = "entradas.eventos"
TIEMPO_RESPUESTA_SEGUNDOS = 5.0
MAX_ENTREGAS_EVENTO = 5
PREFETCH = 20

Identidad = dict[str, Any] | None
ManejadorAccion = Callable[[dict, Identidad], Awaitable[Any]]
ManejadorEvento = Callable[[dict], Awaitable[None]]

log = logging.getLogger("mensajeria")


class Bus:
    """Conexión de un servicio al bus. Registra manejadores y luego llama a `conectar`."""

    def __init__(self, url: str, servicio: str) -> None:
        self._url = url
        self.servicio = servicio
        self._acciones: dict[str, ManejadorAccion] = {}
        self._eventos: dict[str, ManejadorEvento] = {}
        self._pendientes: dict[str, asyncio.Future] = {}
        self._conexion = None
        self._canal = None
        self._exchange = None
        self._cola_respuestas = None

    def accion(self, nombre: str) -> Callable[[ManejadorAccion], ManejadorAccion]:
        """Registra una acción que otros servicios pueden pedir."""

        def registrar(manejador: ManejadorAccion) -> ManejadorAccion:
            self._acciones[nombre] = manejador
            return manejador

        return registrar

    def al_recibir(self, tipo: str) -> Callable[[ManejadorEvento], ManejadorEvento]:
        """Registra un manejador de eventos. Debe ser idempotente: pueden llegar repetidos."""

        def registrar(manejador: ManejadorEvento) -> ManejadorEvento:
            self._eventos[tipo] = manejador
            return manejador

        return registrar

    async def conectar(self) -> None:
        # connect_robust reconecta y restaura colas y consumidores si RabbitMQ se reinicia.
        self._conexion = await aio_pika.connect_robust(self._url)
        # on_return_raises: un mensaje que ninguna cola recibiría lanza error en vez de perderse.
        self._canal = await self._conexion.channel(publisher_confirms=True, on_return_raises=True)
        await self._canal.set_qos(prefetch_count=PREFETCH)
        self._exchange = await self._canal.declare_exchange(
            EXCHANGE_EVENTOS, aio_pika.ExchangeType.TOPIC, durable=True
        )
        self._cola_respuestas = await self._canal.declare_queue(exclusive=True, auto_delete=True)
        await self._cola_respuestas.consume(self._al_recibir_respuesta, no_ack=True)

        if self._acciones:
            cola = await self._canal.declare_queue(f"rpc.{self.servicio}", durable=True)
            await cola.consume(self._atender_accion)
        if self._eventos:
            cola = await self._canal.declare_queue(
                f"{self.servicio}.eventos",
                durable=True,
                arguments={"x-queue-type": "quorum", "x-delivery-limit": MAX_ENTREGAS_EVENTO},
            )
            for tipo in self._eventos:
                await cola.bind(self._exchange, routing_key=tipo)
            await cola.consume(self._atender_evento)

    async def cerrar(self) -> None:
        if self._conexion:
            await self._conexion.close()

    async def pedir(
        self,
        servicio: str,
        accion: str,
        datos: dict | None = None,
        identidad: Identidad = None,
        tiempo: float = TIEMPO_RESPUESTA_SEGUNDOS,
    ) -> Any:
        """Pide una acción a otro servicio y espera la respuesta."""
        correlacion = str(uuid.uuid4())
        futuro = asyncio.get_running_loop().create_future()
        self._pendientes[correlacion] = futuro
        cuerpo = {"accion": accion, "identidad": identidad, "datos": datos or {}}
        try:
            await self._canal.default_exchange.publish(
                aio_pika.Message(
                    json.dumps(cuerpo).encode(),
                    content_type="application/json",
                    correlation_id=correlacion,
                    reply_to=self._cola_respuestas.name,
                    # Si nadie la atiende a tiempo, se descarta: quien pidió ya dejó de esperar.
                    expiration=tiempo,
                ),
                routing_key=f"rpc.{servicio}",
            )
            respuesta = await asyncio.wait_for(futuro, tiempo)
        except (TimeoutError, aio_pika.exceptions.DeliveryError) as error:
            raise SinRespuesta(f"{servicio}.{accion} no respondió") from error
        finally:
            self._pendientes.pop(correlacion, None)

        if respuesta["ok"]:
            return respuesta["datos"]
        raise ErrorDeNegocio(respuesta["error"]["codigo"], respuesta["error"]["mensaje"])

    async def publicar(self, tipo: str, datos: dict) -> None:
        """Publica un evento persistente. Falla si ninguna cola lo recibiría."""
        evento = {
            "id": str(uuid.uuid4()),
            "tipo": tipo,
            "ocurrido_en": datetime.now(UTC).isoformat(),
            "datos": datos,
        }
        await self._exchange.publish(
            aio_pika.Message(
                json.dumps(evento).encode(),
                content_type="application/json",
                message_id=evento["id"],
                delivery_mode=aio_pika.DeliveryMode.PERSISTENT,
            ),
            routing_key=tipo,
        )

    async def _al_recibir_respuesta(self, mensaje: AbstractIncomingMessage) -> None:
        futuro = self._pendientes.get(mensaje.correlation_id or "")
        # Una respuesta tardía no tiene a nadie esperándola: se ignora.
        if futuro and not futuro.done():
            futuro.set_result(json.loads(mensaje.body))

    async def _atender_accion(self, mensaje: AbstractIncomingMessage) -> None:
        # Se confirma siempre: un pedido no se reintenta porque quien lo hizo tiene un plazo.
        async with mensaje.process(requeue=False):
            respuesta = await self._ejecutar_accion(mensaje.body)
            if mensaje.reply_to:
                await self._canal.default_exchange.publish(
                    aio_pika.Message(
                        json.dumps(respuesta, default=str).encode(),
                        content_type="application/json",
                        correlation_id=mensaje.correlation_id,
                    ),
                    routing_key=mensaje.reply_to,
                )

    async def _ejecutar_accion(self, cuerpo: bytes) -> dict:
        nombre = "?"
        try:
            pedido = json.loads(cuerpo)
            nombre = pedido["accion"]
            manejador = self._acciones.get(nombre)
            if manejador is None:
                raise ErrorDeNegocio("validacion", f"Acción desconocida: {nombre}")
            datos = await manejador(pedido.get("datos") or {}, pedido.get("identidad"))
            return {"ok": True, "datos": datos}
        except ErrorDeNegocio as error:
            return _respuesta_de_error(error.codigo, error.mensaje)
        except ValidationError as error:
            campos = ", ".join(str(e["loc"][-1]) for e in error.errors() if e["loc"])
            return _respuesta_de_error("validacion", f"Datos inválidos: {campos or 'cuerpo'}")
        except Exception:
            # El detalle queda en el log; al cliente no se le filtra nada interno.
            log.exception("Error inesperado en %s.%s", self.servicio, nombre)
            return _respuesta_de_error("interno", "Error interno")

    async def _atender_evento(self, mensaje: AbstractIncomingMessage) -> None:
        # Si el manejador falla, vuelve a la cola; tras MAX_ENTREGAS_EVENTO RabbitMQ lo descarta.
        async with mensaje.process(requeue=True):
            evento = json.loads(mensaje.body)
            manejador = self._eventos.get(evento["tipo"])
            if manejador:
                await manejador(evento["datos"])


def _respuesta_de_error(codigo: str, mensaje: str) -> dict:
    return {"ok": False, "error": {"codigo": codigo, "mensaje": mensaje}}


async def ejecutar_servicio(bus: Bus, tareas: list[Callable[[], Awaitable[None]]] = ()) -> None:
    """Conecta el bus y corre hasta recibir una señal de término, para apagarse limpio en Docker."""
    logging.basicConfig(level=logging.INFO, format="%(asctime)s %(name)s %(levelname)s %(message)s")
    await bus.conectar()
    log.info("Servicio %s listo", bus.servicio)

    detener = asyncio.Event()
    loop = asyncio.get_running_loop()
    for senal in (signal.SIGTERM, signal.SIGINT):
        loop.add_signal_handler(senal, detener.set)

    en_curso = [asyncio.create_task(tarea()) for tarea in tareas]
    await detener.wait()
    for tarea in en_curso:
        tarea.cancel()
    await bus.cerrar()
