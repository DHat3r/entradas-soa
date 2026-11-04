"""Cada servicio usa su propio esquema: search_path evita leer tablas ajenas por accidente."""

import contextlib
import os
import uuid
from collections.abc import AsyncIterator

from sqlalchemy import MetaData, text
from sqlalchemy.ext.asyncio import (
    AsyncEngine,
    AsyncSession,
    async_sessionmaker,
    create_async_engine,
)

URL_DE_PRUEBA = "postgresql+asyncpg://entradas:cambia-esto-en-local@localhost:5432/entradas"

Sesiones = async_sessionmaker[AsyncSession]


def crear_motor(url: str, esquema: str, **opciones) -> AsyncEngine:
    return create_async_engine(
        url,
        connect_args={"server_settings": {"search_path": esquema}},
        pool_pre_ping=True,
        **opciones,
    )


def crear_sesiones(motor: AsyncEngine) -> Sesiones:
    return async_sessionmaker(motor, expire_on_commit=False)


@contextlib.asynccontextmanager
async def sesiones_de_prueba(metadata: MetaData) -> AsyncIterator[Sesiones]:
    """Crea un esquema desechable con las tablas, para que los tests no se pisen entre sí."""
    url = os.getenv("TEST_DATABASE_URL", URL_DE_PRUEBA)
    esquema = f"prueba_{uuid.uuid4().hex[:12]}"
    # Tamaño alto: los tests de concurrencia abren muchas conexiones a la vez.
    motor = crear_motor(url, esquema, pool_size=20, max_overflow=40)
    async with motor.begin() as conexion:
        await conexion.execute(text(f'CREATE SCHEMA "{esquema}"'))
        await conexion.run_sync(metadata.create_all)
    try:
        yield crear_sesiones(motor)
    finally:
        async with motor.begin() as conexion:
            await conexion.execute(text(f'DROP SCHEMA "{esquema}" CASCADE'))
        await motor.dispose()
