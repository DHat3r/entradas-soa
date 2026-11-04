import uuid

import pytest
from basedatos import sesiones_de_prueba
from mensajeria import BusDePrueba
from pydantic import ValidationError
from sqlalchemy import select

from app.modelos import Base, Pago
from app.procesador import registrar_procesador

RESERVA = str(uuid.uuid4())


@pytest.fixture
async def sesiones():
    async with sesiones_de_prueba(Base.metadata) as creadas:
        yield creadas


@pytest.fixture
def bus(sesiones):
    bus = BusDePrueba("pagos")
    registrar_procesador(bus, sesiones)
    return bus


def pedido(resultado="aprobar", monto=30000) -> dict:
    return {"reserva_id": RESERVA, "monto_clp": monto, "resultado_simulado": resultado}


def tipos(bus) -> list[str]:
    return [tipo for tipo, _ in bus.publicados]


async def pagos_guardados(sesiones) -> list[Pago]:
    async with sesiones() as sesion:
        return list(await sesion.scalars(select(Pago)))


async def test_aprobar_guarda_aprobado_y_publica_pago_aprobado(bus, sesiones):
    await bus.entregar("pago.solicitado", pedido("aprobar"))

    pagos = await pagos_guardados(sesiones)
    assert [pago.estado for pago in pagos] == ["APROBADO"]
    tipo, datos = bus.publicados[-1]
    assert tipo == "pago.aprobado"
    assert datos == {"reserva_id": RESERVA, "pago_id": str(pagos[0].id)}


async def test_rechazar_guarda_rechazado_y_publica_pago_rechazado(bus, sesiones):
    await bus.entregar("pago.solicitado", pedido("rechazar"))

    pagos = await pagos_guardados(sesiones)
    assert [pago.estado for pago in pagos] == ["RECHAZADO"]
    tipo, datos = bus.publicados[-1]
    assert tipo == "pago.rechazado"
    assert datos == {"reserva_id": RESERVA, "pago_id": str(pagos[0].id)}


async def test_mensaje_repetido_deja_un_solo_pago_y_publica_el_mismo_pago(bus, sesiones):
    await bus.entregar("pago.solicitado", pedido("aprobar"))
    await bus.entregar("pago.solicitado", pedido("aprobar"))

    pagos = await pagos_guardados(sesiones)
    assert len(pagos) == 1
    assert tipos(bus) == ["pago.aprobado", "pago.aprobado"]
    assert bus.publicados[0][1]["pago_id"] == bus.publicados[1][1]["pago_id"] == str(pagos[0].id)


async def test_repetido_con_resultado_distinto_conserva_el_resultado_original(bus, sesiones):
    await bus.entregar("pago.solicitado", pedido("aprobar"))
    await bus.entregar("pago.solicitado", pedido("rechazar"))

    pagos = await pagos_guardados(sesiones)
    assert [pago.estado for pago in pagos] == ["APROBADO"]
    assert tipos(bus) == ["pago.aprobado", "pago.aprobado"]


async def test_si_publicar_falla_no_queda_pago_y_al_reintentar_funciona(bus, sesiones):
    publicar_real = bus.publicar

    async def publicar_que_falla(tipo, datos):
        raise ConnectionError("RabbitMQ caído")

    bus.publicar = publicar_que_falla
    with pytest.raises(ConnectionError):
        await bus.entregar("pago.solicitado", pedido("aprobar"))
    assert await pagos_guardados(sesiones) == []

    bus.publicar = publicar_real
    await bus.entregar("pago.solicitado", pedido("aprobar"))

    assert len(await pagos_guardados(sesiones)) == 1
    assert tipos(bus) == ["pago.aprobado"]


@pytest.mark.parametrize("datos", [pedido(resultado="quizas"), pedido(monto=-1)])
async def test_datos_invalidos_no_se_procesan(bus, datos):
    with pytest.raises(ValidationError):
        await bus.entregar("pago.solicitado", datos)

    assert bus.publicados == []
