import asyncio
import uuid
from datetime import UTC, datetime, timedelta

import pytest
from basedatos import sesiones_de_prueba
from mensajeria import BusDePrueba, ErrorDeNegocio, SinRespuesta
from sqlalchemy import select

from app.modelos import Base, Reserva
from app.saga import registrar_saga, vencer_reservas

ANA = {"usuario_id": str(uuid.uuid4()), "rol": "cliente", "correo": "ana@correo.cl"}
BETO = {"usuario_id": str(uuid.uuid4()), "rol": "cliente", "correo": "beto@correo.cl"}
SECTOR = str(uuid.uuid4())
CUPOS = {
    "evento_id": str(uuid.uuid4()),
    "evento_nombre": "Concierto",
    "sector_nombre": "General",
    "precio_clp": 15000,
}


@pytest.fixture
async def sesiones():
    async with sesiones_de_prueba(Base.metadata) as creadas:
        yield creadas


@pytest.fixture
def bus(sesiones):
    bus = BusDePrueba("reservas")
    bus.respuestas[("eventos", "apartar_cupos")] = CUPOS
    registrar_saga(bus, sesiones)
    return bus


async def nueva_reserva(bus, cantidad=2, identidad=ANA) -> dict:
    return await bus.llamar("crear", {"sector_id": SECTOR, "cantidad": cantidad}, identidad)


async def estado(sesiones, reserva_id: str) -> str:
    async with sesiones() as sesion:
        reserva = await sesion.get(Reserva, uuid.UUID(reserva_id))
    return reserva.estado


async def pagando(bus) -> dict:
    reserva = await nueva_reserva(bus)
    await bus.llamar("pagar", {"reserva_id": reserva["id"], "resultado_simulado": "aprobar"}, ANA)
    return reserva


async def vencer_plazo(sesiones, reserva_id: str) -> None:
    async with sesiones() as sesion:
        reserva = await sesion.get(Reserva, uuid.UUID(reserva_id))
        reserva.vence_en = datetime.now(UTC) - timedelta(seconds=1)
        await sesion.commit()


def tipos(bus) -> list[str]:
    return [tipo for tipo, _ in bus.publicados]


async def test_crear_aparta_cupos_y_calcula_el_monto_con_el_precio_del_servidor(bus):
    reserva = await bus.llamar("crear", {"sector_id": SECTOR, "cantidad": 2, "monto_clp": 1}, ANA)

    assert reserva["estado"] == "PENDIENTE_PAGO"
    assert reserva["monto_clp"] == 30000
    assert reserva["evento_nombre"] == "Concierto"


async def test_crear_exige_ser_cliente(bus):
    with pytest.raises(ErrorDeNegocio) as sin_sesion:
        await bus.llamar("crear", {"sector_id": SECTOR, "cantidad": 1})
    with pytest.raises(ErrorDeNegocio) as organizador:
        await bus.llamar(
            "crear", {"sector_id": SECTOR, "cantidad": 1}, {**ANA, "rol": "organizador"}
        )

    assert sin_sesion.value.codigo == "no_autorizado"
    assert organizador.value.codigo == "prohibido"


@pytest.mark.parametrize("cantidad", [0, 7, -1])
async def test_crear_rechaza_cantidades_fuera_de_rango(bus, cantidad):
    with pytest.raises(ErrorDeNegocio) as error:
        await nueva_reserva(bus, cantidad=cantidad)

    assert error.value.codigo == "validacion"


async def test_sin_cupos_cancela_sin_publicar_nada_que_liberar(bus, sesiones):
    bus.respuestas[("eventos", "apartar_cupos")] = ErrorDeNegocio("conflicto", "Sin cupos")

    with pytest.raises(ErrorDeNegocio) as error:
        await nueva_reserva(bus)

    assert error.value.codigo == "conflicto"
    assert bus.publicados == []
    async with sesiones() as sesion:
        reserva = await sesion.scalar(select(Reserva))
    assert reserva.estado == "CANCELADA"


async def test_sin_respuesta_de_eventos_cancela_y_compensa_por_si_alcanzo_a_apartar(bus):
    bus.respuestas[("eventos", "apartar_cupos")] = SinRespuesta("eventos no respondió")

    with pytest.raises(ErrorDeNegocio) as error:
        await nueva_reserva(bus)

    assert error.value.codigo == "no_disponible"
    assert tipos(bus) == ["reserva.cancelada"]
    assert bus.publicados[0][1]["motivo"] == "error"
    assert bus.publicados[0][1]["sector_id"] == SECTOR


async def test_pagar_pasa_a_pagando_y_solicita_el_pago(bus, sesiones):
    reserva = await pagando(bus)

    assert await estado(sesiones, reserva["id"]) == "PAGANDO"
    assert tipos(bus) == ["pago.solicitado"]
    assert bus.publicados[0][1]["monto_clp"] == 30000
    assert bus.publicados[0][1]["resultado_simulado"] == "aprobar"


async def test_pagar_dos_veces_solicita_un_solo_pago(bus):
    reserva = await pagando(bus)

    with pytest.raises(ErrorDeNegocio) as error:
        await bus.llamar(
            "pagar", {"reserva_id": reserva["id"], "resultado_simulado": "aprobar"}, ANA
        )

    assert error.value.codigo == "conflicto"
    assert tipos(bus) == ["pago.solicitado"]


async def test_no_se_puede_pagar_una_reserva_ajena(bus):
    reserva = await nueva_reserva(bus)

    with pytest.raises(ErrorDeNegocio) as error:
        await bus.llamar(
            "pagar", {"reserva_id": reserva["id"], "resultado_simulado": "aprobar"}, BETO
        )

    assert error.value.codigo == "no_encontrado"
    assert bus.publicados == []


async def test_no_se_puede_pagar_con_el_plazo_vencido_aunque_no_haya_corrido_el_vencimiento(
    bus, sesiones
):
    reserva = await nueva_reserva(bus)
    await vencer_plazo(sesiones, reserva["id"])

    with pytest.raises(ErrorDeNegocio) as error:
        await bus.llamar(
            "pagar", {"reserva_id": reserva["id"], "resultado_simulado": "aprobar"}, ANA
        )

    assert error.value.codigo == "conflicto"


async def test_si_publicar_el_pago_falla_la_reserva_sigue_pendiente(bus, sesiones):
    reserva = await nueva_reserva(bus)

    async def publicar_que_falla(tipo, datos):
        raise ConnectionError("RabbitMQ caído")

    bus.publicar = publicar_que_falla

    with pytest.raises(ConnectionError):
        await bus.llamar(
            "pagar", {"reserva_id": reserva["id"], "resultado_simulado": "aprobar"}, ANA
        )

    assert await estado(sesiones, reserva["id"]) == "PENDIENTE_PAGO"


async def test_pago_aprobado_confirma_y_avisa_a_entradas(bus, sesiones):
    reserva = await pagando(bus)

    await bus.entregar("pago.aprobado", {"reserva_id": reserva["id"], "pago_id": "p1"})

    assert await estado(sesiones, reserva["id"]) == "CONFIRMADA"
    tipo, datos = bus.publicados[-1]
    assert tipo == "reserva.confirmada"
    assert datos["cliente_correo"] == ANA["correo"]
    assert datos["cantidad"] == 2


async def test_pago_aprobado_repetido_confirma_una_sola_vez(bus):
    reserva = await pagando(bus)
    evento = {"reserva_id": reserva["id"], "pago_id": "p1"}

    await asyncio.gather(*(bus.entregar("pago.aprobado", evento) for _ in range(5)))

    assert tipos(bus).count("reserva.confirmada") == 1


async def test_pago_rechazado_libera_los_cupos(bus, sesiones):
    reserva = await pagando(bus)

    await bus.entregar("pago.rechazado", {"reserva_id": reserva["id"], "pago_id": "p1"})

    assert await estado(sesiones, reserva["id"]) == "RECHAZADA"
    tipo, datos = bus.publicados[-1]
    assert tipo == "reserva.cancelada"
    assert datos["motivo"] == "rechazada"


async def test_si_publicar_la_confirmacion_falla_el_reintento_vuelve_a_intentarlo(bus, sesiones):
    reserva = await pagando(bus)
    publicar_real = bus.publicar

    async def publicar_que_falla(tipo, datos):
        raise ConnectionError("RabbitMQ caído")

    bus.publicar = publicar_que_falla
    with pytest.raises(ConnectionError):
        await bus.entregar("pago.aprobado", {"reserva_id": reserva["id"]})
    assert await estado(sesiones, reserva["id"]) == "PAGANDO"

    bus.publicar = publicar_real
    await bus.entregar("pago.aprobado", {"reserva_id": reserva["id"]})

    assert await estado(sesiones, reserva["id"]) == "CONFIRMADA"
    assert tipos(bus).count("reserva.confirmada") == 1


async def test_vencimiento_libera_las_reservas_pendientes_con_plazo_vencido(bus, sesiones):
    vencida = await nueva_reserva(bus)
    vigente = await nueva_reserva(bus)
    await vencer_plazo(sesiones, vencida["id"])

    assert await vencer_reservas(bus, sesiones) == 1

    assert await estado(sesiones, vencida["id"]) == "VENCIDA"
    assert await estado(sesiones, vigente["id"]) == "PENDIENTE_PAGO"
    assert bus.publicados[-1][1]["motivo"] == "vencida"


async def test_vencimiento_recupera_reservas_abandonadas_en_creada(bus, sesiones):
    async with sesiones() as sesion:
        abandonada = Reserva(
            id=uuid.uuid4(),
            cliente_id=uuid.UUID(ANA["usuario_id"]),
            cliente_correo=ANA["correo"],
            sector_id=uuid.UUID(SECTOR),
            cantidad=1,
            estado="CREADA",
            vence_en=datetime.now(UTC) - timedelta(seconds=1),
        )
        sesion.add(abandonada)
        await sesion.commit()

    await vencer_reservas(bus, sesiones)

    assert await estado(sesiones, str(abandonada.id)) == "CANCELADA"
    assert bus.publicados[-1][1]["motivo"] == "error"


async def test_una_reserva_pagando_no_vence(bus, sesiones):
    reserva = await pagando(bus)
    await vencer_plazo(sesiones, reserva["id"])

    assert await vencer_reservas(bus, sesiones) == 0

    assert await estado(sesiones, reserva["id"]) == "PAGANDO"


async def test_carrera_entre_pagar_y_vencer_tiene_un_solo_ganador(bus, sesiones):
    for _ in range(10):
        reserva = await nueva_reserva(bus)
        await vencer_plazo(sesiones, reserva["id"])
        bus.publicados.clear()

        await asyncio.gather(
            bus.llamar(
                "pagar", {"reserva_id": reserva["id"], "resultado_simulado": "aprobar"}, ANA
            ),
            vencer_reservas(bus, sesiones),
            return_exceptions=True,
        )

        assert await estado(sesiones, reserva["id"]) == "VENCIDA"
        assert tipos(bus) == ["reserva.cancelada"]


async def test_detalle_de_una_reserva_ajena_no_existe(bus):
    reserva = await nueva_reserva(bus)

    with pytest.raises(ErrorDeNegocio) as error:
        await bus.llamar("detalle", {"reserva_id": reserva["id"]}, BETO)

    assert error.value.codigo == "no_encontrado"


async def test_listar_mias_solo_trae_las_propias(bus):
    await nueva_reserva(bus, identidad=ANA)
    await nueva_reserva(bus, identidad=BETO)

    reservas = await bus.llamar("listar_mias", identidad=ANA)

    assert len(reservas) == 1
