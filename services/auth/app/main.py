import asyncio
import os

from basedatos import crear_motor, crear_sesiones
from mensajeria import Bus, ejecutar_servicio

from app.acciones import registrar_acciones, sembrar_internos


async def main() -> None:
    jwt_secret = os.environ["JWT_SECRET"]
    if len(jwt_secret) < 32:
        raise SystemExit("JWT_SECRET debe tener al menos 32 caracteres")

    sesiones = crear_sesiones(crear_motor(os.environ["DATABASE_URL"], "auth"))
    password = os.environ["SEED_PASSWORD"]
    await sembrar_internos(
        sesiones,
        [
            ("Organización Demo", os.environ["SEED_ORGANIZADOR_CORREO"], password, "organizador"),
            ("Puerta Demo", os.environ["SEED_VALIDADOR_CORREO"], password, "validador"),
        ],
    )

    bus = Bus(os.environ["RABBITMQ_URL"], "auth")
    registrar_acciones(bus, sesiones, jwt_secret)
    await ejecutar_servicio(bus)


if __name__ == "__main__":
    asyncio.run(main())
