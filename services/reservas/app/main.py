import asyncio
import os

from basedatos import crear_motor, crear_sesiones
from mensajeria import Bus, ejecutar_servicio

from app.saga import registrar_saga, tarea_de_reparacion, tarea_de_vencimiento


async def main() -> None:
    sesiones = crear_sesiones(crear_motor(os.environ["DATABASE_URL"], "reservas"))
    bus = Bus(os.environ["RABBITMQ_URL"], "reservas")
    registrar_saga(bus, sesiones)
    await ejecutar_servicio(
        bus,
        [
            lambda: tarea_de_vencimiento(bus, sesiones),
            lambda: tarea_de_reparacion(bus, sesiones),
        ],
    )


if __name__ == "__main__":
    asyncio.run(main())
