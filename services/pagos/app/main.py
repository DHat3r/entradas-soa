import asyncio
import os

from basedatos import crear_motor, crear_sesiones
from mensajeria import Bus, ejecutar_servicio

from app.procesador import registrar_procesador


async def main() -> None:
    sesiones = crear_sesiones(crear_motor(os.environ["DATABASE_URL"], "pagos"))
    bus = Bus(os.environ["RABBITMQ_URL"], "pagos")
    registrar_procesador(bus, sesiones)
    await ejecutar_servicio(bus)


if __name__ == "__main__":
    asyncio.run(main())
