import uuid
from datetime import UTC, datetime

from basedatos import Sesiones
from mensajeria import ErrorDeNegocio, exigir_rol
from pydantic import AwareDatetime, BaseModel, Field
from sqlalchemy import select

from app.modelos import Evento, Sector


class SectorNuevo(BaseModel):
    nombre: str = Field(min_length=1, max_length=80)
    # Tope para que el total de una compra de 6 entradas quepa en un entero de 32 bits.
    precio_clp: int = Field(ge=0, le=10_000_000)
    capacidad: int = Field(ge=1, le=100000)


class EventoNuevo(BaseModel):
    nombre: str = Field(min_length=1, max_length=160)
    descripcion: str = Field(default="", max_length=2000)
    lugar: str = Field(min_length=1, max_length=160)
    fecha: AwareDatetime
    sectores: list[SectorNuevo] = Field(min_length=1, max_length=10)


class EventoPorId(BaseModel):
    evento_id: uuid.UUID


def a_dict(evento: Evento) -> dict:
    return {
        "id": str(evento.id),
        "nombre": evento.nombre,
        "descripcion": evento.descripcion,
        "lugar": evento.lugar,
        "fecha": evento.fecha.isoformat(),
        "estado": evento.estado,
        "organizador_id": str(evento.organizador_id),
        "sectores": [
            {
                "id": str(sector.id),
                "nombre": sector.nombre,
                "precio_clp": sector.precio_clp,
                "capacidad": sector.capacidad,
                "disponibles": sector.disponibles,
                "vendidos": sector.capacidad - sector.disponibles,
            }
            for sector in evento.sectores
        ],
    }


def a_dict_publico(evento: Evento) -> dict:
    """Lo que ve cualquiera: sin quién organiza ni cuánto se ha vendido."""
    datos = a_dict(evento)
    del datos["organizador_id"]
    for sector in datos["sectores"]:
        del sector["vendidos"]
    return datos


def _es_organizador_de(evento: Evento, identidad: dict | None) -> bool:
    return (
        identidad is not None
        and identidad["rol"] == "organizador"
        and evento.organizador_id == uuid.UUID(identidad["usuario_id"])
    )


def registrar_acciones(bus, sesiones: Sesiones) -> None:
    @bus.accion("crear")
    async def crear(datos: dict, identidad) -> dict:
        exigir_rol(identidad, "organizador")
        nuevo = EventoNuevo(**datos)
        if nuevo.fecha <= datetime.now(UTC):
            raise ErrorDeNegocio("validacion", "La fecha del evento debe ser futura")
        # El organizador sale de la identidad: los datos del cliente nunca deciden el dueño.
        evento = Evento(
            organizador_id=uuid.UUID(identidad["usuario_id"]),
            nombre=nuevo.nombre,
            descripcion=nuevo.descripcion,
            lugar=nuevo.lugar,
            fecha=nuevo.fecha,
            estado="BORRADOR",
            sectores=[
                Sector(
                    nombre=sector.nombre,
                    precio_clp=sector.precio_clp,
                    capacidad=sector.capacidad,
                    disponibles=sector.capacidad,
                )
                for sector in nuevo.sectores
            ],
        )
        async with sesiones() as sesion:
            sesion.add(evento)
            await sesion.commit()
        return a_dict(evento)

    @bus.accion("publicar")
    async def publicar(datos: dict, identidad) -> dict:
        exigir_rol(identidad, "organizador")
        pedido = EventoPorId(**datos)
        async with sesiones() as sesion:
            evento = await sesion.get(Evento, pedido.evento_id)
            # Si no es suyo, responde igual que si no existiera: no revela que el evento existe.
            if evento is None or not _es_organizador_de(evento, identidad):
                raise ErrorDeNegocio("no_encontrado", "Evento no encontrado")
            if evento.estado != "PUBLICADO":
                evento.estado = "PUBLICADO"
                await sesion.commit()
        return a_dict(evento)

    @bus.accion("listar_publicados")
    async def listar_publicados(datos: dict, identidad) -> list[dict]:
        async with sesiones() as sesion:
            eventos = (
                await sesion.scalars(
                    select(Evento)
                    .where(Evento.estado == "PUBLICADO", Evento.fecha > datetime.now(UTC))
                    .order_by(Evento.fecha)
                )
            ).all()
        return [a_dict_publico(evento) for evento in eventos]

    @bus.accion("detalle")
    async def detalle(datos: dict, identidad) -> dict:
        pedido = EventoPorId(**datos)
        async with sesiones() as sesion:
            evento = await sesion.get(Evento, pedido.evento_id)
        if evento is None:
            raise ErrorDeNegocio("no_encontrado", "Evento no encontrado")
        # Un borrador solo lo ve su organizador: para los demás no existe.
        if _es_organizador_de(evento, identidad):
            return a_dict(evento)
        if evento.estado != "PUBLICADO":
            raise ErrorDeNegocio("no_encontrado", "Evento no encontrado")
        return a_dict_publico(evento)

    @bus.accion("listar_mios")
    async def listar_mios(datos: dict, identidad) -> list[dict]:
        exigir_rol(identidad, "organizador")
        async with sesiones() as sesion:
            eventos = (
                await sesion.scalars(
                    select(Evento)
                    .where(Evento.organizador_id == uuid.UUID(identidad["usuario_id"]))
                    .order_by(Evento.fecha)
                )
            ).all()
        return [a_dict(evento) for evento in eventos]
