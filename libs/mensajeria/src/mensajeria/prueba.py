"""Bus en memoria para probar un servicio sin RabbitMQ."""

from typing import Any

from pydantic import ValidationError

from mensajeria.errores import ErrorDeNegocio


class BusDePrueba:
    """Misma interfaz que Bus. Guarda lo publicado y responde lo que se le indique."""

    def __init__(self, servicio: str = "prueba") -> None:
        self.servicio = servicio
        self.publicados: list[tuple[str, dict]] = []
        self.pedidos: list[tuple[str, str, dict]] = []
        self.identidades: list[dict | None] = []
        self.respuestas: dict[tuple[str, str], Any] = {}
        self._acciones: dict = {}
        self._eventos: dict = {}

    def accion(self, nombre: str):
        def registrar(manejador):
            self._acciones[nombre] = manejador
            return manejador

        return registrar

    def al_recibir(self, tipo: str):
        def registrar(manejador):
            self._eventos[tipo] = manejador
            return manejador

        return registrar

    async def pedir(self, servicio, accion, datos=None, identidad=None, tiempo=None) -> Any:
        self.pedidos.append((servicio, accion, datos or {}))
        self.identidades.append(identidad)
        respuesta = self.respuestas[(servicio, accion)]
        if isinstance(respuesta, Exception):
            raise respuesta
        return respuesta

    async def publicar(self, tipo: str, datos: dict) -> None:
        self.publicados.append((tipo, datos))

    async def llamar(self, accion: str, datos: dict | None = None, identidad=None) -> Any:
        """Ejecuta una acción registrada. Traduce validación igual que el bus real."""
        try:
            return await self._acciones[accion](datos or {}, identidad)
        except ValidationError as error:
            raise ErrorDeNegocio("validacion", "Datos inválidos") from error

    async def entregar(self, tipo: str, datos: dict) -> None:
        """Simula la llegada de un evento."""
        await self._eventos[tipo](datos)
