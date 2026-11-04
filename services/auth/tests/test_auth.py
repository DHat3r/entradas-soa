import jwt
import pytest
from basedatos import sesiones_de_prueba
from mensajeria import BusDePrueba, ErrorDeNegocio
from sqlalchemy import select

from app.acciones import registrar_acciones, sembrar_internos
from app.modelos import Base, Usuario

SECRETO = "secreto-de-prueba-con-mas-de-32-caracteres"
ANA = {"nombre": "Ana Pérez", "correo": "Ana@Correo.cl", "password": "Clave1234"}


@pytest.fixture
async def sesiones():
    async with sesiones_de_prueba(Base.metadata) as creadas:
        yield creadas


@pytest.fixture
def bus(sesiones):
    bus = BusDePrueba("auth")
    registrar_acciones(bus, sesiones, SECRETO)
    return bus


async def test_registro_crea_un_cliente_con_correo_normalizado(bus):
    usuario = await bus.llamar("registrar", ANA)

    assert usuario["rol"] == "cliente"
    assert usuario["correo"] == "ana@correo.cl"
    assert "password" not in usuario and "password_hash" not in usuario


async def test_registro_ignora_un_rol_enviado_por_el_cliente(bus):
    usuario = await bus.llamar("registrar", {**ANA, "rol": "organizador"})

    assert usuario["rol"] == "cliente"


async def test_la_contrasena_no_se_guarda_en_texto_plano(bus, sesiones):
    await bus.llamar("registrar", ANA)

    async with sesiones() as sesion:
        guardado = await sesion.scalar(select(Usuario.password_hash))

    assert ANA["password"] not in guardado
    assert guardado.startswith("$argon2")


async def test_correo_repetido_da_conflicto_sin_importar_mayusculas(bus):
    await bus.llamar("registrar", ANA)

    with pytest.raises(ErrorDeNegocio) as error:
        await bus.llamar("registrar", {**ANA, "correo": "ana@correo.cl"})

    assert error.value.codigo == "conflicto"


@pytest.mark.parametrize(
    "cambio",
    [{"password": "corta"}, {"correo": "no-es-correo"}, {"nombre": ""}, {"password": "x" * 129}],
)
async def test_registro_rechaza_datos_invalidos(bus, cambio):
    with pytest.raises(ErrorDeNegocio) as error:
        await bus.llamar("registrar", {**ANA, **cambio})

    assert error.value.codigo == "validacion"


async def test_login_devuelve_un_token_con_la_identidad(bus):
    creado = await bus.llamar("registrar", ANA)

    respuesta = await bus.llamar("login", {"correo": "ana@correo.cl", "password": ANA["password"]})

    claims = jwt.decode(respuesta["token"], SECRETO, algorithms=["HS256"])
    assert claims["sub"] == creado["id"]
    assert claims["rol"] == "cliente"
    assert claims["exp"] > claims["iat"]


@pytest.mark.parametrize(
    "credenciales",
    [
        {"correo": "ana@correo.cl", "password": "ClaveMala1"},
        {"correo": "nadie@correo.cl", "password": "Clave1234"},
    ],
)
async def test_login_falla_con_el_mismo_mensaje_si_la_clave_o_el_correo_son_malos(
    bus, credenciales
):
    await bus.llamar("registrar", ANA)

    with pytest.raises(ErrorDeNegocio) as error:
        await bus.llamar("login", credenciales)

    assert error.value.codigo == "no_autorizado"
    assert error.value.mensaje == "Correo o contraseña incorrectos"


async def test_seed_crea_cuentas_internas_una_sola_vez(sesiones, bus):
    cuentas = [("Org", "org@entradas.dev", "Clave1234", "organizador")]

    await sembrar_internos(sesiones, cuentas)
    await sembrar_internos(sesiones, cuentas)

    respuesta = await bus.llamar("login", {"correo": "org@entradas.dev", "password": "Clave1234"})
    assert respuesta["usuario"]["rol"] == "organizador"
    async with sesiones() as sesion:
        assert len((await sesion.scalars(select(Usuario))).all()) == 1
