"""Recorre la compra completa contra el stack real levantado con docker compose.

Va por nginx, igual que un navegador, y comprueba que el correo llegue a Mailpit.
"""

import asyncio
import os
import time
import uuid
from datetime import UTC, datetime, timedelta

import httpx
import pytest

WEB = os.getenv("E2E_WEB_URL", "http://localhost:8080")
MAILPIT = os.getenv("E2E_MAILPIT_URL", "http://localhost:8025")
PASSWORD_SEED = "Demo1234!"
ESPERA_SAGA_SEGUNDOS = 20


def ingresar(correo: str, password: str) -> httpx.Client:
    cliente = httpx.Client(base_url=f"{WEB}/api", timeout=15)
    # El gateway limita los intentos de login por minuto: si se corre seguido, hay que esperar.
    for _ in range(8):
        respuesta = cliente.post("/auth/login", json={"correo": correo, "password": password})
        if respuesta.status_code != 429:
            break
        time.sleep(10)
    assert respuesta.status_code == 200, respuesta.text
    return cliente


@pytest.fixture(scope="module")
def organizador():
    return ingresar("organizador@entradas.dev", PASSWORD_SEED)


@pytest.fixture(scope="module")
def puerta():
    return ingresar("validador@entradas.dev", PASSWORD_SEED)


@pytest.fixture(scope="module")
def correo_cliente():
    return f"e2e-{uuid.uuid4().hex[:8]}@correo.cl"


@pytest.fixture(scope="module")
def comprador(correo_cliente):
    datos = {"nombre": "Prueba E2E", "correo": correo_cliente, "password": "Clave1234"}
    assert httpx.post(f"{WEB}/api/auth/registro", json=datos, timeout=15).status_code == 201
    return ingresar(correo_cliente, "Clave1234")


def crear_evento(organizador: httpx.Client, capacidad: int = 10, precio: int = 15000) -> dict:
    respuesta = organizador.post(
        "/eventos",
        json={
            "nombre": f"Evento E2E {uuid.uuid4().hex[:6]}",
            "lugar": "Teatro",
            "fecha": (datetime.now(UTC) + timedelta(days=30)).isoformat(),
            "sectores": [{"nombre": "General", "precio_clp": precio, "capacidad": capacidad}],
        },
    )
    assert respuesta.status_code == 201, respuesta.text
    evento = respuesta.json()
    assert organizador.post(f"/eventos/{evento['id']}/publicar").status_code == 200
    return evento


def disponibles(evento_id: str) -> int:
    evento = httpx.get(f"{WEB}/api/eventos/{evento_id}", timeout=15).json()
    return evento["sectores"][0]["disponibles"]


def esperar(condicion, descripcion: str):
    limite = time.monotonic() + ESPERA_SAGA_SEGUNDOS
    while time.monotonic() < limite:
        resultado = condicion()
        if resultado:
            return resultado
        time.sleep(0.25)
    pytest.fail(f"No ocurrió a tiempo: {descripcion}")


def reservar_y_pagar(comprador: httpx.Client, sector_id: str, cantidad: int, resultado: str) -> str:
    respuesta = comprador.post("/reservas", json={"sector_id": sector_id, "cantidad": cantidad})
    assert respuesta.status_code == 201, respuesta.text
    reserva_id = respuesta.json()["id"]
    pago = comprador.post(f"/reservas/{reserva_id}/pagar", json={"resultado_simulado": resultado})
    assert pago.status_code == 202, pago.text
    return reserva_id


def estado_de(comprador: httpx.Client, reserva_id: str) -> str:
    return comprador.get(f"/reservas/{reserva_id}").json()["estado"]


def entradas_de(comprador: httpx.Client, evento: dict) -> list[dict]:
    todas = comprador.get("/entradas").json()
    return [e for e in todas if e["evento_nombre"] == evento["nombre"]]


def test_compra_aprobada_emite_entradas_envia_correo_y_el_qr_entra_una_vez(
    organizador, comprador, puerta, correo_cliente
):
    evento = crear_evento(organizador)
    sector = evento["sectores"][0]

    reserva_id = reservar_y_pagar(comprador, sector["id"], 2, "aprobar")

    esperar(lambda: estado_de(comprador, reserva_id) == "CONFIRMADA", "confirmar la reserva")
    assert disponibles(evento["id"]) == 8
    assert comprador.get(f"/reservas/{reserva_id}").json()["monto_clp"] == 30000

    entradas = esperar(lambda: entradas_de(comprador, evento), "emitir las entradas")
    assert len(entradas) == 2

    def buscar_correo():
        busqueda = httpx.get(
            f"{MAILPIT}/api/v1/search", params={"query": f"to:{correo_cliente}"}, timeout=15
        ).json()
        return [m for m in busqueda["messages"] if evento["nombre"] in m["Subject"]]

    correo = esperar(buscar_correo, "recibir el correo")[0]
    detalle = httpx.get(f"{MAILPIT}/api/v1/message/{correo['ID']}", timeout=15).json()
    assert [a["ContentType"] for a in detalle["Attachments"]] == ["image/png", "image/png"]

    codigo = entradas[0]["codigo"]
    assert puerta.post("/entradas/validar", json={"codigo": codigo}).json()["resultado"] == "valida"
    segunda = puerta.post("/entradas/validar", json={"codigo": codigo}).json()
    assert segunda["resultado"] == "ya_usada"


def test_pago_rechazado_libera_el_cupo_y_no_emite_entradas(organizador, comprador):
    evento = crear_evento(organizador)
    sector = evento["sectores"][0]

    reserva_id = reservar_y_pagar(comprador, sector["id"], 3, "rechazar")

    esperar(lambda: estado_de(comprador, reserva_id) == "RECHAZADA", "rechazar la reserva")
    esperar(lambda: disponibles(evento["id"]) == 10, "liberar los cupos")
    assert entradas_de(comprador, evento) == []


def test_compras_simultaneas_no_sobrevenden(organizador, comprador):
    evento = crear_evento(organizador, capacidad=5)
    sector_id = evento["sectores"][0]["id"]

    async def comprar_todos():
        async with httpx.AsyncClient(
            base_url=f"{WEB}/api", cookies=comprador.cookies, timeout=30
        ) as cliente:
            return await asyncio.gather(
                *(
                    cliente.post("/reservas", json={"sector_id": sector_id, "cantidad": 1})
                    for _ in range(25)
                )
            )

    estados = [r.status_code for r in asyncio.run(comprar_todos())]

    assert estados.count(201) == 5
    assert estados.count(409) == 20
    assert disponibles(evento["id"]) == 0


def test_un_cliente_no_puede_entrar_al_sistema_interno(comprador):
    assert comprador.get("/interno/eventos").status_code == 403
    assert comprador.post("/entradas/validar", json={"codigo": "x"}).status_code == 403
    assert comprador.post("/eventos", json={}).status_code == 403


def test_sin_sesion_no_se_puede_comprar():
    respuesta = httpx.post(
        f"{WEB}/api/reservas", json={"sector_id": str(uuid.uuid4()), "cantidad": 1}, timeout=15
    )

    assert respuesta.status_code == 401


def test_el_registro_publico_no_permite_elegir_rol():
    correo = f"e2e-{uuid.uuid4().hex[:8]}@correo.cl"
    respuesta = httpx.post(
        f"{WEB}/api/auth/registro",
        json={"nombre": "Colada", "correo": correo, "password": "Clave1234", "rol": "organizador"},
        timeout=15,
    )

    assert respuesta.json()["rol"] == "cliente"
