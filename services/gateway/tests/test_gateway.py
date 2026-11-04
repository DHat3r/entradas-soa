from datetime import UTC, datetime, timedelta

import jwt
import pytest
from fastapi.testclient import TestClient
from mensajeria import BusDePrueba, ErrorDeNegocio, SinRespuesta

from app.main import COOKIE_SESION, Ajustes, LimitadorDeIntentos, crear_app

SECRETO = "secreto-de-prueba-con-mas-de-32-caracteres"


def token(rol="cliente", secreto=SECRETO, vence_en=timedelta(hours=1)) -> str:
    claims = {
        "sub": "u1",
        "rol": rol,
        "correo": "a@b.cl",
        "nombre": "Ana",
        "exp": datetime.now(UTC) + vence_en,
    }
    return jwt.encode(claims, secreto, algorithm="HS256")


@pytest.fixture
def bus():
    return BusDePrueba("gateway")


@pytest.fixture
def cliente(bus):
    app = crear_app(bus, Ajustes(jwt_secret=SECRETO, cookie_secure=False), conectar_bus=False)
    return TestClient(app)


def ultimo_identidad(bus: BusDePrueba) -> dict | None:
    return bus.identidades[-1]


def test_health_responde_ok(cliente):
    assert cliente.get("/api/health").json() == {"estado": "ok"}


def test_login_guarda_la_sesion_en_una_cookie_httponly_y_estricta(cliente, bus):
    bus.respuestas[("auth", "login")] = {"token": token(), "usuario": {"id": "u1"}}

    respuesta = cliente.post("/api/auth/login", json={"correo": "a@b.cl", "password": "x"})

    cookie = respuesta.headers["set-cookie"].lower()
    assert respuesta.status_code == 200
    assert f"{COOKIE_SESION}=" in cookie
    assert "httponly" in cookie
    assert "samesite=strict" in cookie
    assert "token" not in respuesta.json()


def test_login_se_bloquea_tras_demasiados_intentos(cliente, bus):
    bus.respuestas[("auth", "login")] = ErrorDeNegocio("no_autorizado", "Credenciales malas")
    credenciales = {"correo": "a@b.cl", "password": "mala"}

    estados = [cliente.post("/api/auth/login", json=credenciales).status_code for _ in range(6)]

    assert estados == [401] * 5 + [429]


def test_limitador_vuelve_a_permitir_cuando_pasa_la_ventana():
    reloj = [0.0]
    limitador = LimitadorDeIntentos(ahora=lambda: reloj[0])

    for _ in range(5):
        assert limitador.permitir("ip")
    assert not limitador.permitir("ip")

    reloj[0] = 61.0
    assert limitador.permitir("ip")


def test_la_identidad_viene_del_token_y_no_del_cuerpo(cliente, bus):
    bus.respuestas[("reservas", "crear")] = {"id": "r1"}

    cliente.post(
        "/api/reservas",
        json={"sector_id": "s1", "cantidad": 1, "usuario_id": "otra-persona"},
        headers={"Authorization": f"Bearer {token()}"},
    )

    assert ultimo_identidad(bus)["usuario_id"] == "u1"


def test_la_cookie_tambien_identifica(cliente, bus):
    bus.respuestas[("entradas", "listar_mias")] = []
    cliente.cookies.set(COOKIE_SESION, token())

    cliente.get("/api/entradas")

    assert ultimo_identidad(bus)["usuario_id"] == "u1"


@pytest.mark.parametrize(
    "malo",
    [
        "no-es-un-jwt",
        token(secreto="otro-secreto-con-mas-de-32-caracteres-aqui"),
        token(vence_en=timedelta(hours=-1)),
    ],
)
def test_un_token_invalido_equivale_a_no_tener_sesion(cliente, bus, malo):
    bus.respuestas[("entradas", "listar_mias")] = []

    cliente.get("/api/entradas", headers={"Authorization": f"Bearer {malo}"})

    assert ultimo_identidad(bus) is None


def test_token_con_algoritmo_none_se_rechaza(cliente, bus):
    bus.respuestas[("entradas", "listar_mias")] = []
    forjado = jwt.encode(
        {"sub": "u1", "rol": "organizador", "correo": "a@b.cl", "nombre": "A"},
        key="",
        algorithm="none",
    )

    cliente.get("/api/entradas", headers={"Authorization": f"Bearer {forjado}"})

    assert ultimo_identidad(bus) is None


@pytest.mark.parametrize(
    ("codigo", "estado"),
    [
        ("validacion", 422),
        ("no_autorizado", 401),
        ("prohibido", 403),
        ("no_encontrado", 404),
        ("conflicto", 409),
        ("interno", 500),
    ],
)
def test_errores_de_negocio_se_traducen_a_http(cliente, bus, codigo, estado):
    bus.respuestas[("eventos", "listar_publicados")] = ErrorDeNegocio(codigo, "mensaje")

    respuesta = cliente.get("/api/eventos")

    assert respuesta.status_code == estado
    assert respuesta.json() == {"codigo": codigo, "mensaje": "mensaje"}


def test_servicio_sin_respuesta_da_504(cliente, bus):
    bus.respuestas[("eventos", "listar_publicados")] = SinRespuesta("eventos.listar no respondió")

    assert cliente.get("/api/eventos").status_code == 504


def test_el_gateway_no_expone_la_accion_interna_de_apartar_cupos(cliente):
    rutas = {ruta.path for ruta in cliente.app.routes}

    assert not any("apartar" in ruta for ruta in rutas)


def test_pagar_usa_el_id_de_la_ruta_aunque_el_cuerpo_traiga_otro(cliente, bus):
    bus.respuestas[("reservas", "pagar")] = {"id": "r1"}

    cliente.post(
        "/api/reservas/r1/pagar",
        json={"reserva_id": "ajena", "resultado_simulado": "aprobar"},
        headers={"Authorization": f"Bearer {token()}"},
    )

    assert bus.pedidos[-1][2]["reserva_id"] == "r1"


def test_registro_se_bloquea_tras_demasiados_intentos(cliente, bus):
    bus.respuestas[("auth", "registrar")] = {"id": "u1"}

    estados = [cliente.post("/api/auth/registro", json={}).status_code for _ in range(6)]

    assert estados == [201] * 5 + [429]
