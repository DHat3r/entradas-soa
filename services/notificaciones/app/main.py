import asyncio
import os

from basedatos import crear_motor, crear_sesiones
from mensajeria import Bus, ejecutar_servicio

from app.correo import EnviadorSmtp
from app.notificador import registrar_notificador


async def main() -> None:
    sesiones = crear_sesiones(crear_motor(os.environ["DATABASE_URL"], "notificaciones"))
    bus = Bus(os.environ["RABBITMQ_URL"], "notificaciones")
    remitente = os.environ["CORREO_REMITENTE"]
    enviador = EnviadorSmtp(os.environ["SMTP_HOST"], int(os.environ["SMTP_PUERTO"]))
    registrar_notificador(bus, sesiones, enviador, remitente)
    await ejecutar_servicio(bus)


if __name__ == "__main__":
    asyncio.run(main())
