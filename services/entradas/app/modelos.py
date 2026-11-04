import uuid
from datetime import datetime

from sqlalchemy import DateTime, Index, Integer, String, UniqueConstraint, func
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column


class Base(DeclarativeBase):
    pass


class Entrada(Base):
    __tablename__ = "entradas"
    __table_args__ = (
        # Evita emitir dos veces la misma entrada si el evento llega repetido.
        UniqueConstraint("reserva_id", "numero", name="entradas_reserva_numero_key"),
        Index("ix_entradas_cliente_id", "cliente_id"),
    )

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    reserva_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True))
    numero: Mapped[int] = mapped_column(Integer)
    cliente_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True))
    cliente_correo: Mapped[str] = mapped_column(String(254))
    evento_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True))
    evento_nombre: Mapped[str] = mapped_column(String(160))
    sector_nombre: Mapped[str] = mapped_column(String(80))
    usada_en: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    emitida_en: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
