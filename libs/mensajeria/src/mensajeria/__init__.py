"""Comunicación entre servicios por RabbitMQ. El contrato está en docs/arquitectura.md."""

from mensajeria.bus import Bus, avisar_si_secreto_de_ejemplo, ejecutar_servicio
from mensajeria.errores import ErrorDeNegocio, SinRespuesta, exigir_rol
from mensajeria.prueba import BusDePrueba

__all__ = [
    "Bus",
    "BusDePrueba",
    "ErrorDeNegocio",
    "SinRespuesta",
    "avisar_si_secreto_de_ejemplo",
    "ejecutar_servicio",
    "exigir_rol",
]
