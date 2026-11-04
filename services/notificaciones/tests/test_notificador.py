import asyncio
import uuid

import pytest
from basedatos import sesiones_de_prueba
from mensajeria import BusDePrueba
from pydantic import ValidationError
from sqlalchemy import func, select

from app.modelos import Base, CorreoEnviado
from app.notificador import registrar_notificador

REMITENTE = "entradas@entradas.local"
PNG = b"\x89PNG\r\n\x1a\n"


def evento(**cambios) -> dict:
    datos = {
        "reserva_id": str(uuid.uuid4()),
        "cliente_correo": "ana@correo.cl",
        "evento_nombre": "Concierto",
        "sector_nombre": "General",
        "entradas": [
            {"id": str(uuid.uuid4()), "codigo": "ENTRADA-1"},
            {"id": str(uuid.uuid4()), "codigo": "ENTRADA-2"},
        ],
    }
    return {**datos, **cambios}


class EnviadorFalso:
    def __init__(self) -> None:
        self.enviados = []
        self.fallar = False

    async def enviar(self, mensaje) -> None:
        if self.fallar:
            raise ConnectionError("SMTP caído")
        self.enviados.append(mensaje)


@pytest.fixture
async def sesiones():
    async with sesiones_de_prueba(Base.metadata) as creadas:
        yield creadas


@pytest.fixture
def enviador():
    return EnviadorFalso()


@pytest.fixture
def bus(sesiones, enviador):
    bus = BusDePrueba("notificaciones")
    registrar_notificador(bus, sesiones, enviador, REMITENTE)
    return bus


async def cantidad_de_correos(sesiones) -> int:
    async with sesiones() as sesion:
        return await sesion.scalar(select(func.count()).select_from(CorreoEnviado))


async def test_envia_el_correo_con_asunto_y_un_png_por_entrada(bus, enviador):
    await bus.entregar("entradas.emitidas", evento())

    assert len(enviador.enviados) == 1
    mensaje = enviador.enviados[0]
    assert mensaje["To"] == "ana@correo.cl"
    assert mensaje["From"] == REMITENTE
    assert mensaje["Subject"] == "Tus entradas para Concierto"
    adjuntos = list(mensaje.iter_attachments())
    assert [adjunto.get_filename() for adjunto in adjuntos] == ["entrada-1.png", "entrada-2.png"]
    for adjunto in adjuntos:
        assert adjunto.get_content_type() == "image/png"
        assert adjunto.get_payload(decode=True).startswith(PNG)


async def test_evento_repetido_no_reenvia_el_correo(bus, sesiones, enviador):
    datos = evento()

    await bus.entregar("entradas.emitidas", datos)
    await bus.entregar("entradas.emitidas", datos)

    assert len(enviador.enviados) == 1
    assert await cantidad_de_correos(sesiones) == 1


async def test_si_el_envio_falla_no_queda_fila_y_el_reintento_envia(bus, sesiones, enviador):
    datos = evento()
    enviador.fallar = True

    with pytest.raises(ConnectionError):
        await bus.entregar("entradas.emitidas", datos)

    assert await cantidad_de_correos(sesiones) == 0
    assert enviador.enviados == []

    enviador.fallar = False
    await bus.entregar("entradas.emitidas", datos)

    assert len(enviador.enviados) == 1
    assert await cantidad_de_correos(sesiones) == 1


async def test_el_html_escapa_el_nombre_del_evento(bus, enviador):
    await bus.entregar("entradas.emitidas", evento(evento_nombre="<script>alert('x')</script>"))

    html = enviador.enviados[0].get_body(preferencelist=("html",)).get_content()
    assert "<script>" not in html
    assert "&lt;script&gt;" in html


async def test_datos_invalidos_lanzan_validation_error(bus, enviador):
    sin_correo = evento()
    del sin_correo["cliente_correo"]

    with pytest.raises(ValidationError):
        await bus.entregar("entradas.emitidas", sin_correo)

    assert enviador.enviados == []


async def test_un_salto_de_linea_en_el_nombre_no_impide_enviar_el_correo(bus, enviador):
    await bus.entregar("entradas.emitidas", evento(evento_nombre="Concierto\nBcc: otro@correo.cl"))

    mensaje = enviador.enviados[0]
    assert mensaje["Subject"] == "Tus entradas para Concierto Bcc: otro@correo.cl"
    assert mensaje["Bcc"] is None


async def test_copias_simultaneas_del_evento_envian_un_solo_correo(bus, enviador):
    datos = evento()

    await asyncio.gather(*(bus.entregar("entradas.emitidas", datos) for _ in range(5)))

    assert len(enviador.enviados) == 1
