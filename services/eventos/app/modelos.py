import uuid
from datetime import datetime

from sqlalchemy import Boolean, CheckConstraint, DateTime, ForeignKey, Integer, String, Text, func
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column, relationship


class Base(DeclarativeBase):
    pass


class Evento(Base):
    __tablename__ = "eventos"
    __table_args__ = (CheckConstraint("estado IN ('BORRADOR', 'PUBLICADO')", name="estado_valido"),)

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    organizador_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True))
    nombre: Mapped[str] = mapped_column(String(160))
    descripcion: Mapped[str] = mapped_column(Text)
    lugar: Mapped[str] = mapped_column(String(160))
    fecha: Mapped[datetime] = mapped_column(DateTime(timezone=True))
    estado: Mapped[str] = mapped_column(String(20), default="BORRADOR")
    creado_en: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())

    sectores: Mapped[list["Sector"]] = relationship(lazy="selectin", order_by="Sector.precio_clp")


class Sector(Base):
    __tablename__ = "sectores"
    __table_args__ = (
        CheckConstraint("precio_clp >= 0", name="precio_no_negativo"),
        CheckConstraint("capacidad > 0", name="capacidad_positiva"),
        CheckConstraint(
            "disponibles >= 0 AND disponibles <= capacidad", name="disponibles_en_rango"
        ),
    )

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    evento_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("eventos.id", ondelete="CASCADE"), index=True
    )
    nombre: Mapped[str] = mapped_column(String(80))
    precio_clp: Mapped[int] = mapped_column(Integer)
    capacidad: Mapped[int] = mapped_column(Integer)
    disponibles: Mapped[int] = mapped_column(Integer)


class Apartado(Base):
    """Cupos tomados por una reserva. Hace idempotente apartar y liberar."""

    __tablename__ = "apartados"

    reserva_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True)
    sector_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("sectores.id"))
    cantidad: Mapped[int] = mapped_column(Integer)
    liberado: Mapped[bool] = mapped_column(Boolean, default=False)
