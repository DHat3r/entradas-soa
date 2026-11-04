import asyncio
import os

from basedatos import crear_motor, crear_sesiones
from mensajeria import Bus, ejecutar_servicio

from app.acciones import registrar_acciones


async def main() -> None:
    qr_secret = os.environ["QR_SECRET"]
    if len(qr_secret) < 32:
        raise SystemExit("QR_SECRET debe tener al menos 32 caracteres")

    sesiones = crear_sesiones(crear_motor(os.environ["DATABASE_URL"], "entradas"))
    bus = Bus(os.environ["RABBITMQ_URL"], "entradas")
    registrar_acciones(bus, sesiones, qr_secret)
    await ejecutar_servicio(bus)


if __name__ == "__main__":
    asyncio.run(main())
