import asyncio
import os

from basedatos import crear_motor, crear_sesiones
from mensajeria import Bus, ejecutar_servicio

from app.acciones import registrar_acciones
from app.cupos import registrar_cupos


async def main() -> None:
    sesiones = crear_sesiones(crear_motor(os.environ["DATABASE_URL"], "eventos"))

    bus = Bus(os.environ["RABBITMQ_URL"], "eventos")
    registrar_acciones(bus, sesiones)
    registrar_cupos(bus, sesiones)
    await ejecutar_servicio(bus)


if __name__ == "__main__":
    asyncio.run(main())
