import asyncio
import uuid
from datetime import UTC, datetime, timedelta

import pytest
from basedatos import sesiones_de_prueba
from mensajeria import BusDePrueba, ErrorDeNegocio

from app.acciones import registrar_acciones
from app.cupos import registrar_cupos
from app.modelos import Base, Evento, Sector

ORGANIZADOR = {"usuario_id": str(uuid.uuid4()), "rol": "organizador", "correo": "o@e.dev"}


@pytest.fixture
async def sesiones():
    async with sesiones_de_prueba(Base.metadata) as creadas:
        yield creadas


@pytest.fixture
def bus(sesiones):
    bus = BusDePrueba("eventos")
    registrar_acciones(bus, sesiones)
    registrar_cupos(bus, sesiones)
    return bus


async def crear_sector(bus, capacidad=10, publicar=True) -> str:
    evento = await bus.llamar(
        "crear",
        {
            "nombre": "Concierto",
            "lugar": "Estadio",
            "fecha": datetime.now(UTC) + timedelta(days=30),
            "sectores": [{"nombre": "General", "precio_clp": 15000, "capacidad": capacidad}],
        },
        ORGANIZADOR,
    )
    if publicar:
        await bus.llamar("publicar", {"evento_id": evento["id"]}, ORGANIZADOR)
    return evento["sectores"][0]["id"]


async def disponibles(sesiones, sector_id: str) -> int:
    async with sesiones() as sesion:
        sector = await sesion.get(Sector, uuid.UUID(sector_id))
    return sector.disponibles


def pedido(sector_id: str, cantidad: int = 1, reserva_id: str | None = None) -> dict:
    return {
        "reserva_id": reserva_id or str(uuid.uuid4()),
        "sector_id": sector_id,
        "cantidad": cantidad,
    }


async def test_apartar_descuenta_y_devuelve_el_precio_del_servidor(bus, sesiones):
    sector_id = await crear_sector(bus)

    respuesta = await bus.llamar("apartar_cupos", pedido(sector_id, 3))

    assert respuesta["precio_clp"] == 15000
    assert respuesta["evento_nombre"] == "Concierto"
    assert await disponibles(sesiones, sector_id) == 7


async def test_cincuenta_compras_simultaneas_por_diez_cupos_no_sobrevenden(bus, sesiones):
    sector_id = await crear_sector(bus, capacidad=10)

    resultados = await asyncio.gather(
        *(bus.llamar("apartar_cupos", pedido(sector_id)) for _ in range(50)),
        return_exceptions=True,
    )

    exitosas = [r for r in resultados if isinstance(r, dict)]
    rechazadas = [r for r in resultados if isinstance(r, ErrorDeNegocio)]
    assert len(exitosas) == 10
    assert len(rechazadas) == 40
    assert all(r.codigo == "conflicto" for r in rechazadas)
    assert await disponibles(sesiones, sector_id) == 0


async def test_apartar_dos_veces_la_misma_reserva_descuenta_una_vez(bus, sesiones):
    sector_id = await crear_sector(bus)
    mismo = pedido(sector_id, 2)

    await bus.llamar("apartar_cupos", mismo)
    await bus.llamar("apartar_cupos", mismo)

    assert await disponibles(sesiones, sector_id) == 8


async def test_sin_cupos_no_deja_un_apartado_que_luego_sume_al_liberar(bus, sesiones):
    sector_id = await crear_sector(bus, capacidad=1)
    sin_cupo = pedido(sector_id, 2)

    with pytest.raises(ErrorDeNegocio):
        await bus.llamar("apartar_cupos", sin_cupo)
    await bus.entregar(
        "reserva.cancelada", {"reserva_id": sin_cupo["reserva_id"], "sector_id": sector_id}
    )

    assert await disponibles(sesiones, sector_id) == 1


async def test_no_se_puede_apartar_en_un_borrador(bus):
    sector_id = await crear_sector(bus, publicar=False)

    with pytest.raises(ErrorDeNegocio) as error:
        await bus.llamar("apartar_cupos", pedido(sector_id))

    assert error.value.codigo == "no_encontrado"


async def test_no_se_puede_apartar_en_un_evento_pasado(bus, sesiones):
    sector_id = await crear_sector(bus)
    async with sesiones() as sesion:
        sector = await sesion.get(Sector, uuid.UUID(sector_id))
        evento = await sesion.get(Evento, sector.evento_id)
        evento.fecha = datetime.now(UTC) - timedelta(days=1)
        await sesion.commit()

    with pytest.raises(ErrorDeNegocio) as error:
        await bus.llamar("apartar_cupos", pedido(sector_id))

    assert error.value.codigo == "conflicto"


async def test_cancelar_libera_los_cupos(bus, sesiones):
    sector_id = await crear_sector(bus)
    apartado = pedido(sector_id, 4)
    await bus.llamar("apartar_cupos", apartado)

    await bus.entregar("reserva.cancelada", {**apartado, "motivo": "rechazada"})

    assert await disponibles(sesiones, sector_id) == 10


async def test_cancelacion_repetida_libera_una_sola_vez(bus, sesiones):
    sector_id = await crear_sector(bus)
    await bus.llamar("apartar_cupos", pedido(sector_id, 2))
    apartado = pedido(sector_id, 4)
    await bus.llamar("apartar_cupos", apartado)

    evento = {"reserva_id": apartado["reserva_id"], "sector_id": sector_id}
    await asyncio.gather(*(bus.entregar("reserva.cancelada", evento) for _ in range(5)))

    assert await disponibles(sesiones, sector_id) == 8


async def test_apartar_atrasado_despues_de_cancelar_no_toma_cupos(bus, sesiones):
    sector_id = await crear_sector(bus)
    atrasado = pedido(sector_id, 3)

    await bus.entregar(
        "reserva.cancelada", {"reserva_id": atrasado["reserva_id"], "sector_id": sector_id}
    )
    with pytest.raises(ErrorDeNegocio) as error:
        await bus.llamar("apartar_cupos", atrasado)

    assert error.value.codigo == "conflicto"
    assert await disponibles(sesiones, sector_id) == 10
