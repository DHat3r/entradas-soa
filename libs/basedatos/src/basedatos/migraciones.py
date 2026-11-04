"""Lógica común de los env.py de Alembic: cada servicio solo indica su metadata y esquema."""

import asyncio
import os

from alembic import context
from sqlalchemy import MetaData, text
from sqlalchemy.engine import Connection

from basedatos import crear_motor


def ejecutar(metadata: MetaData, esquema: str) -> None:
    asyncio.run(_migrar(metadata, esquema))


async def _migrar(metadata: MetaData, esquema: str) -> None:
    motor = crear_motor(os.environ["DATABASE_URL"], esquema)
    async with motor.connect() as conexion:
        await conexion.execute(text(f'CREATE SCHEMA IF NOT EXISTS "{esquema}"'))
        await conexion.commit()
        await conexion.run_sync(_correr, metadata)
        await conexion.commit()
    await motor.dispose()


def _correr(conexion: Connection, metadata: MetaData) -> None:
    # search_path ya apunta al esquema del servicio, así que alembic_version queda ahí también.
    context.configure(connection=conexion, target_metadata=metadata)
    with context.begin_transaction():
        context.run_migrations()
