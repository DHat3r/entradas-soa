import uuid
from datetime import UTC, datetime, timedelta

import pytest
from basedatos import sesiones_de_prueba
from mensajeria import BusDePrueba, ErrorDeNegocio
from sqlalchemy import select

from app.acciones import registrar_acciones
from app.modelos import Base, Evento, Sector

ORGANIZADOR = {"usuario_id": str(uuid.uuid4()), "rol": "organizador", "correo": "org@entradas.dev"}
CLIENTE = {"usuario_id": str(uuid.uuid4()), "rol": "cliente", "correo": "ana@correo.cl"}
SECTOR = {"nombre": "General", "precio_clp": 15000, "capacidad": 100}


def futura(dias: int = 30) -> datetime:
    return datetime.now(UTC) + timedelta(days=dias)


EVENTO = {
    "nombre": "Concierto",
    "descripcion": "Gira 2026",
    "lugar": "Estadio",
    "fecha": futura(),
    "sectores": [SECTOR],
}


@pytest.fixture
async def sesiones():
    async with sesiones_de_prueba(Base.metadata) as creadas:
        yield creadas


@pytest.fixture
def bus(sesiones):
    bus = BusDePrueba("eventos")
    registrar_acciones(bus, sesiones)
    return bus


async def publicar_nuevo(bus, nombre="Concierto", fecha=None):
    creado = await bus.llamar(
        "crear", {**EVENTO, "nombre": nombre, "fecha": fecha or futura()}, ORGANIZADOR
    )
    return await bus.llamar("publicar", {"evento_id": creado["id"]}, ORGANIZADOR)


async def test_crear_toma_el_organizador_de_la_identidad(bus):
    evento = await bus.llamar("crear", {**EVENTO, "organizador_id": str(uuid.uuid4())}, ORGANIZADOR)

    assert evento["organizador_id"] == ORGANIZADOR["usuario_id"]


async def test_crear_deja_borrador_con_cupos_disponibles_completos(bus):
    evento = await bus.llamar("crear", EVENTO, ORGANIZADOR)

    assert evento["estado"] == "BORRADOR"
    assert evento["sectores"][0]["disponibles"] == SECTOR["capacidad"]


async def test_cliente_no_puede_crear_eventos(bus):
    with pytest.raises(ErrorDeNegocio) as error:
        await bus.llamar("crear", EVENTO, CLIENTE)

    assert error.value.codigo == "prohibido"


async def test_crear_sin_sesion_da_no_autorizado(bus):
    with pytest.raises(ErrorDeNegocio) as error:
        await bus.llamar("crear", EVENTO)

    assert error.value.codigo == "no_autorizado"


@pytest.mark.parametrize(
    "cambio",
    [
        {"sectores": []},
        {"sectores": [{**SECTOR, "capacidad": 0}]},
        {"sectores": [{**SECTOR, "precio_clp": -1}]},
        {"fecha": futura(-1)},
        {"sectores": [SECTOR] * 11},
    ],
)
async def test_crear_rechaza_datos_invalidos(bus, cambio):
    with pytest.raises(ErrorDeNegocio) as error:
        await bus.llamar("crear", {**EVENTO, **cambio}, ORGANIZADOR)

    assert error.value.codigo == "validacion"


async def test_organizador_publica_su_evento(bus):
    creado = await bus.llamar("crear", EVENTO, ORGANIZADOR)

    publicado = await bus.llamar("publicar", {"evento_id": creado["id"]}, ORGANIZADOR)

    assert publicado["estado"] == "PUBLICADO"


async def test_publicar_evento_ajeno_da_no_encontrado(bus):
    creado = await bus.llamar("crear", EVENTO, ORGANIZADOR)

    with pytest.raises(ErrorDeNegocio) as error:
        await bus.llamar(
            "publicar",
            {"evento_id": creado["id"]},
            {**ORGANIZADOR, "usuario_id": str(uuid.uuid4())},
        )

    assert error.value.codigo == "no_encontrado"


async def test_publicar_dos_veces_es_idempotente(bus):
    creado = await bus.llamar("crear", EVENTO, ORGANIZADOR)
    await bus.llamar("publicar", {"evento_id": creado["id"]}, ORGANIZADOR)

    segunda = await bus.llamar("publicar", {"evento_id": creado["id"]}, ORGANIZADOR)

    assert segunda["estado"] == "PUBLICADO"


async def test_listar_publicados_excluye_borradores_y_eventos_pasados(bus, sesiones):
    await publicar_nuevo(bus, nombre="Vigente")
    await bus.llamar("crear", {**EVENTO, "nombre": "Borrador"}, ORGANIZADOR)
    async with sesiones() as sesion:
        sesion.add(
            Evento(
                organizador_id=uuid.UUID(ORGANIZADOR["usuario_id"]),
                nombre="Pasado",
                descripcion="",
                lugar="Estadio",
                fecha=futura(-1),
                estado="PUBLICADO",
            )
        )
        await sesion.commit()

    eventos = await bus.llamar("listar_publicados")

    assert [evento["nombre"] for evento in eventos] == ["Vigente"]


async def test_listar_publicados_ordena_por_fecha(bus):
    await publicar_nuevo(bus, nombre="Lejano", fecha=futura(60))
    await publicar_nuevo(bus, nombre="Cercano", fecha=futura(10))

    eventos = await bus.llamar("listar_publicados")

    assert [evento["nombre"] for evento in eventos] == ["Cercano", "Lejano"]


async def test_detalle_de_borrador_ajeno_da_no_encontrado(bus):
    creado = await bus.llamar("crear", EVENTO, ORGANIZADOR)

    with pytest.raises(ErrorDeNegocio) as error:
        await bus.llamar("detalle", {"evento_id": creado["id"]}, CLIENTE)

    assert error.value.codigo == "no_encontrado"


async def test_detalle_de_borrador_lo_ve_su_organizador(bus):
    creado = await bus.llamar("crear", EVENTO, ORGANIZADOR)

    detalle = await bus.llamar("detalle", {"evento_id": creado["id"]}, ORGANIZADOR)

    assert detalle["id"] == creado["id"]


async def test_detalle_con_evento_id_invalido_da_validacion(bus):
    with pytest.raises(ErrorDeNegocio) as error:
        await bus.llamar("detalle", {"evento_id": "no-es-uuid"})

    assert error.value.codigo == "validacion"


async def test_listar_mios_trae_solo_los_eventos_del_organizador(bus):
    await bus.llamar("crear", {**EVENTO, "nombre": "Mio"}, ORGANIZADOR)
    otro = {**ORGANIZADOR, "usuario_id": str(uuid.uuid4())}
    await bus.llamar("crear", {**EVENTO, "nombre": "Ajeno"}, otro)

    mios = await bus.llamar("listar_mios", identidad=ORGANIZADOR)

    assert [evento["nombre"] for evento in mios] == ["Mio"]


async def test_vendidos_se_calcula_como_capacidad_menos_disponibles(bus, sesiones):
    creado = await bus.llamar("crear", EVENTO, ORGANIZADOR)
    async with sesiones() as sesion:
        sector = await sesion.scalar(select(Sector))
        sector.disponibles = 60
        await sesion.commit()

    detalle = await bus.llamar("detalle", {"evento_id": creado["id"]}, ORGANIZADOR)

    assert detalle["sectores"][0]["vendidos"] == 40


async def test_el_publico_no_ve_organizador_ni_vendidos(bus):
    creado = await bus.llamar("crear", {**EVENTO, "fecha": futura()}, ORGANIZADOR)
    await bus.llamar("publicar", {"evento_id": creado["id"]}, ORGANIZADOR)

    for evento in [
        (await bus.llamar("listar_publicados"))[0],
        await bus.llamar("detalle", {"evento_id": creado["id"]}, CLIENTE),
    ]:
        assert "organizador_id" not in evento
        assert "vendidos" not in evento["sectores"][0]
        assert evento["sectores"][0]["disponibles"] == 100


async def test_rechaza_un_precio_sobre_el_tope(bus):
    sector = {**SECTOR, "precio_clp": 10_000_001}

    with pytest.raises(ErrorDeNegocio) as error:
        await bus.llamar("crear", {**EVENTO, "sectores": [sector]}, ORGANIZADOR)

    assert error.value.codigo == "validacion"
