"""Pruebas contra un RabbitMQ real: lo que importa aquí es cómo se comporta el broker."""

import asyncio
import os
import time
import uuid

import pytest
from aio_pika.exceptions import DeliveryError
from mensajeria import Bus, ErrorDeNegocio, SinRespuesta
from mensajeria.bus import MAX_INTENTOS_EVENTO
from pydantic import BaseModel

URL = os.getenv("RABBITMQ_URL", "amqp://entradas:cambia-esto-en-local@localhost:5672/")


@pytest.fixture
async def buses():
    creados = []

    def crear(servicio: str) -> Bus:
        bus = Bus(URL, servicio)
        creados.append(bus)
        return bus

    yield crear
    for bus in creados:
        for cola in (f"rpc.{bus.servicio}", f"{bus.servicio}.eventos"):
            if bus._canal and (bus._acciones or bus._eventos):
                await bus._canal.queue_delete(cola)
        await bus.cerrar()


def nombre_unico(prefijo: str) -> str:
    return f"{prefijo}-{uuid.uuid4().hex[:8]}"


async def test_pedir_devuelve_lo_que_responde_el_servicio(buses):
    nombre = nombre_unico("eco")
    servicio = buses(nombre)

    @servicio.accion("saludar")
    async def saludar(datos, identidad):
        return {"hola": datos["nombre"], "rol": identidad["rol"]}

    cliente = buses(nombre_unico("cliente"))
    await servicio.conectar()
    await cliente.conectar()

    respuesta = await cliente.pedir(nombre, "saludar", {"nombre": "Ana"}, {"rol": "cliente"})

    assert respuesta == {"hola": "Ana", "rol": "cliente"}


async def test_pedidos_simultaneos_no_se_cruzan_las_respuestas(buses):
    nombre = nombre_unico("eco")
    servicio = buses(nombre)

    @servicio.accion("eco")
    async def eco(datos, identidad):
        await asyncio.sleep(0.01)
        return datos["n"]

    cliente = buses(nombre_unico("cliente"))
    await servicio.conectar()
    await cliente.conectar()

    respuestas = await asyncio.gather(*(cliente.pedir(nombre, "eco", {"n": n}) for n in range(30)))

    assert respuestas == list(range(30))


async def test_error_de_negocio_llega_con_su_codigo(buses):
    nombre = nombre_unico("falla")
    servicio = buses(nombre)

    @servicio.accion("apartar")
    async def apartar(datos, identidad):
        raise ErrorDeNegocio("conflicto", "No quedan cupos")

    cliente = buses(nombre_unico("cliente"))
    await servicio.conectar()
    await cliente.conectar()

    with pytest.raises(ErrorDeNegocio) as error:
        await cliente.pedir(nombre, "apartar")

    assert error.value.codigo == "conflicto"
    assert error.value.mensaje == "No quedan cupos"


async def test_error_inesperado_no_filtra_el_detalle(buses):
    nombre = nombre_unico("falla")
    servicio = buses(nombre)

    @servicio.accion("explotar")
    async def explotar(datos, identidad):
        raise RuntimeError("password=secreta")

    cliente = buses(nombre_unico("cliente"))
    await servicio.conectar()
    await cliente.conectar()

    with pytest.raises(ErrorDeNegocio) as error:
        await cliente.pedir(nombre, "explotar")

    assert error.value.codigo == "interno"
    assert "secreta" not in error.value.mensaje


async def test_datos_invalidos_responden_error_de_validacion(buses):
    class Entrada(BaseModel):
        cantidad: int

    nombre = nombre_unico("valida")
    servicio = buses(nombre)

    @servicio.accion("crear")
    async def crear(datos, identidad):
        return Entrada(**datos).cantidad

    cliente = buses(nombre_unico("cliente"))
    await servicio.conectar()
    await cliente.conectar()

    with pytest.raises(ErrorDeNegocio) as error:
        await cliente.pedir(nombre, "crear", {"cantidad": "muchas"})

    assert error.value.codigo == "validacion"
    assert "cantidad" in error.value.mensaje


async def test_pedir_a_un_servicio_caido_avisa_sin_respuesta(buses):
    cliente = buses(nombre_unico("cliente"))
    await cliente.conectar()

    with pytest.raises(SinRespuesta):
        await cliente.pedir("servicio-que-no-existe", "algo", tiempo=0.2)


async def test_evento_llega_a_quien_se_suscribio(buses):
    tipo = f"prueba.{uuid.uuid4().hex[:8]}"
    recibido = asyncio.get_running_loop().create_future()
    consumidor = buses(nombre_unico("consumidor"))

    @consumidor.al_recibir(tipo)
    async def manejar(datos):
        recibido.set_result(datos)

    publicador = buses(nombre_unico("publicador"))
    await consumidor.conectar()
    await publicador.conectar()

    await publicador.publicar(tipo, {"reserva_id": "r1"})

    assert await asyncio.wait_for(recibido, 5) == {"reserva_id": "r1"}


async def test_evento_con_manejador_que_falla_se_reintenta(buses):
    tipo = f"prueba.{uuid.uuid4().hex[:8]}"
    intentos = []
    logrado = asyncio.get_running_loop().create_future()
    consumidor = buses(nombre_unico("consumidor"))

    @consumidor.al_recibir(tipo)
    async def manejar(datos):
        intentos.append(1)
        if len(intentos) < 3:
            raise RuntimeError("falla temporal")
        logrado.set_result(True)

    publicador = buses(nombre_unico("publicador"))
    await consumidor.conectar()
    await publicador.conectar()

    await publicador.publicar(tipo, {})

    await asyncio.wait_for(logrado, 10)
    assert len(intentos) == 3


async def test_publicar_evento_sin_consumidores_falla_en_vez_de_perderse(buses):
    publicador = buses(nombre_unico("publicador"))
    await publicador.conectar()

    with pytest.raises(DeliveryError):
        await publicador.publicar(f"nadie.{uuid.uuid4().hex[:8]}", {})


async def test_evento_que_siempre_falla_se_descarta_tras_el_maximo_de_intentos(buses):
    tipo = f"prueba.{uuid.uuid4().hex[:8]}"
    entregas = []
    consumidor = Bus(URL, nombre_unico("consumidor"), espera_base=0)
    buses_creados = buses(nombre_unico("publicador"))

    @consumidor.al_recibir(tipo)
    async def manejar(datos):
        entregas.append(1)
        raise RuntimeError("falla permanente")

    await consumidor.conectar()
    await buses_creados.conectar()
    await buses_creados.publicar(tipo, {})

    for _ in range(100):
        await asyncio.sleep(0.1)
        if len(entregas) >= MAX_INTENTOS_EVENTO:
            break
    # Margen para detectar entregas de más.
    await asyncio.sleep(1)
    cantidad = len(entregas)
    await consumidor._canal.queue_delete(f"{consumidor.servicio}.eventos")
    await consumidor.cerrar()

    assert cantidad == MAX_INTENTOS_EVENTO


async def test_reintento_de_evento_espera_antes_de_volver_a_la_cola(buses):
    tipo = f"prueba.{uuid.uuid4().hex[:8]}"
    momentos = []
    logrado = asyncio.get_running_loop().create_future()
    consumidor = Bus(URL, nombre_unico("consumidor"), espera_base=0.3)
    publicador = buses(nombre_unico("publicador"))

    @consumidor.al_recibir(tipo)
    async def manejar(datos):
        momentos.append(time.monotonic())
        if len(momentos) == 1:
            raise RuntimeError("falla temporal")
        logrado.set_result(True)

    await consumidor.conectar()
    await publicador.conectar()
    await publicador.publicar(tipo, {})
    await asyncio.wait_for(logrado, 10)
    await consumidor._canal.queue_delete(f"{consumidor.servicio}.eventos")
    await consumidor.cerrar()

    assert momentos[1] - momentos[0] >= 0.3
