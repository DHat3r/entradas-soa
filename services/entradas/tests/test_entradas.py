import asyncio
import uuid

import pytest
from basedatos import sesiones_de_prueba
from mensajeria import BusDePrueba, ErrorDeNegocio
from sqlalchemy import select

from app.acciones import registrar_acciones
from app.codigos import generar_codigo, leer_codigo
from app.modelos import Base, Entrada

SECRETO = "secreto-de-qr-con-mas-de-32-caracteres"
ANA = {"usuario_id": str(uuid.uuid4()), "rol": "cliente", "correo": "ana@correo.cl"}
BETO = {"usuario_id": str(uuid.uuid4()), "rol": "cliente", "correo": "beto@correo.cl"}
PUERTA = {"usuario_id": str(uuid.uuid4()), "rol": "validador", "correo": "puerta@entradas.dev"}


def confirmada(cantidad=2) -> dict:
    return {
        "reserva_id": str(uuid.uuid4()),
        "cliente_id": ANA["usuario_id"],
        "cliente_correo": ANA["correo"],
        "evento_id": str(uuid.uuid4()),
        "evento_nombre": "Concierto",
        "sector_nombre": "General",
        "cantidad": cantidad,
    }


@pytest.fixture
async def sesiones():
    async with sesiones_de_prueba(Base.metadata) as creadas:
        yield creadas


@pytest.fixture
def bus(sesiones):
    bus = BusDePrueba("entradas")
    registrar_acciones(bus, sesiones, SECRETO)
    return bus


async def emitir_una(bus) -> str:
    await bus.entregar("reserva.confirmada", confirmada(cantidad=1))
    return bus.publicados[-1][1]["entradas"][0]["codigo"]


async def test_emite_una_entrada_por_cupo_y_avisa_a_notificaciones(bus):
    await bus.entregar("reserva.confirmada", confirmada(cantidad=3))

    tipo, datos = bus.publicados[-1]
    assert tipo == "entradas.emitidas"
    assert datos["cliente_correo"] == ANA["correo"]
    assert len(datos["entradas"]) == 3
    assert len({e["codigo"] for e in datos["entradas"]}) == 3


async def test_evento_repetido_no_emite_de_nuevo_y_repite_los_mismos_codigos(bus, sesiones):
    evento = confirmada(cantidad=2)

    await bus.entregar("reserva.confirmada", evento)
    await bus.entregar("reserva.confirmada", evento)

    primero, segundo = bus.publicados
    assert primero[1]["entradas"] == segundo[1]["entradas"]
    async with sesiones() as sesion:
        assert len((await sesion.scalars(select(Entrada))).all()) == 2


async def test_si_publicar_falla_no_quedan_entradas_y_el_reintento_funciona(bus, sesiones):
    evento = confirmada()
    publicar_real = bus.publicar

    async def publicar_que_falla(tipo, datos):
        raise ConnectionError("RabbitMQ caído")

    bus.publicar = publicar_que_falla
    with pytest.raises(ConnectionError):
        await bus.entregar("reserva.confirmada", evento)
    async with sesiones() as sesion:
        assert (await sesion.scalars(select(Entrada))).all() == []

    bus.publicar = publicar_real
    await bus.entregar("reserva.confirmada", evento)

    assert len(bus.publicados[-1][1]["entradas"]) == 2


def test_un_codigo_firmado_se_lee_de_vuelta():
    entrada_id = uuid.uuid4()

    assert leer_codigo(generar_codigo(entrada_id, SECRETO), SECRETO) == entrada_id


@pytest.mark.parametrize(
    "alterar",
    [
        lambda c: c[:-1] + ("A" if c[-1] != "A" else "B"),
        lambda c: f"{uuid.uuid4()}.{c.split('.')[1]}",
        lambda c: c.split(".")[0],
        lambda c: "no-es-un-uuid.firma",
        lambda c: "",
    ],
)
def test_un_codigo_alterado_no_se_acepta(alterar):
    codigo = generar_codigo(uuid.uuid4(), SECRETO)

    assert leer_codigo(alterar(codigo), SECRETO) is None


def test_un_codigo_firmado_con_otro_secreto_no_se_acepta():
    codigo = generar_codigo(uuid.uuid4(), "otro-secreto-con-mas-de-32-caracteres-x")

    assert leer_codigo(codigo, SECRETO) is None


async def test_validar_deja_entrar_una_sola_vez(bus):
    codigo = await emitir_una(bus)

    primera = await bus.llamar("validar", {"codigo": codigo}, PUERTA)
    segunda = await bus.llamar("validar", {"codigo": codigo}, PUERTA)

    assert primera["resultado"] == "valida"
    assert primera["entrada"]["evento_nombre"] == "Concierto"
    assert segunda["resultado"] == "ya_usada"


async def test_escaneos_simultaneos_dejan_entrar_a_uno_solo(bus):
    codigo = await emitir_una(bus)

    resultados = await asyncio.gather(
        *(bus.llamar("validar", {"codigo": codigo}, PUERTA) for _ in range(20))
    )

    assert [r["resultado"] for r in resultados].count("valida") == 1


async def test_codigo_alterado_se_rechaza_sin_marcar_nada(bus):
    codigo = await emitir_una(bus)
    alterado = codigo[:-1] + ("A" if codigo[-1] != "A" else "B")

    rechazo = await bus.llamar("validar", {"codigo": alterado}, PUERTA)
    original = await bus.llamar("validar", {"codigo": codigo}, PUERTA)

    assert rechazo["resultado"] == "invalida"
    assert original["resultado"] == "valida"


async def test_codigo_bien_firmado_de_una_entrada_inexistente_no_se_encuentra(bus):
    codigo = generar_codigo(uuid.uuid4(), SECRETO)

    with pytest.raises(ErrorDeNegocio) as error:
        await bus.llamar("validar", {"codigo": codigo}, PUERTA)

    assert error.value.codigo == "no_encontrado"


@pytest.mark.parametrize(
    ("identidad", "codigo_error"), [(None, "no_autorizado"), (ANA, "prohibido")]
)
async def test_validar_exige_un_rol_interno(bus, identidad, codigo_error):
    codigo = await emitir_una(bus)

    with pytest.raises(ErrorDeNegocio) as error:
        await bus.llamar("validar", {"codigo": codigo}, identidad)

    assert error.value.codigo == codigo_error


async def test_listar_mias_trae_las_propias_con_qr(bus):
    await bus.entregar("reserva.confirmada", confirmada(cantidad=2))

    mias = await bus.llamar("listar_mias", identidad=ANA)
    ajenas = await bus.llamar("listar_mias", identidad=BETO)

    assert len(mias) == 2
    assert mias[0]["qr"].startswith("data:image/svg+xml")
    validacion = await bus.llamar("validar", {"codigo": mias[0]["codigo"]}, PUERTA)
    assert validacion["resultado"] == "valida"
    assert ajenas == []


async def test_si_el_commit_falla_tras_publicar_la_reentrega_genera_los_mismos_codigos(bus):
    evento = confirmada(cantidad=2)
    publicar_real = bus.publicar

    async def publicar_y_luego_fallar(tipo, datos):
        await publicar_real(tipo, datos)
        raise ConnectionError("cae justo después de publicar")

    bus.publicar = publicar_y_luego_fallar
    with pytest.raises(ConnectionError):
        await bus.entregar("reserva.confirmada", evento)

    bus.publicar = publicar_real
    await bus.entregar("reserva.confirmada", evento)

    primero, segundo = bus.publicados
    assert primero[1]["entradas"] == segundo[1]["entradas"]
    codigo = primero[1]["entradas"][0]["codigo"]
    assert (await bus.llamar("validar", {"codigo": codigo}, PUERTA))["resultado"] == "valida"
