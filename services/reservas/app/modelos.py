import uuid
from datetime import datetime

from sqlalchemy import Boolean, CheckConstraint, DateTime, Index, Integer, String, func
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column
from sqlalchemy.sql.expression import false


class Base(DeclarativeBase):
    pass


class Reserva(Base):
    __tablename__ = "reservas"
    __table_args__ = (
        CheckConstraint(
            "estado IN ('CREADA', 'CANCELADA', 'PENDIENTE_PAGO', 'VENCIDA', 'PAGANDO', "
            "'CONFIRMADA', 'RECHAZADA')",
            name="estado_valido",
        ),
        CheckConstraint("cantidad BETWEEN 1 AND 6", name="cantidad_valida"),
        # El vencimiento busca por estado y fecha cada pocos segundos.
        Index("ix_reservas_estado_vence_en", "estado", "vence_en"),
        Index("ix_reservas_cliente_id", "cliente_id"),
    )

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    cliente_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True))
    cliente_correo: Mapped[str] = mapped_column(String(254))
    sector_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True))
    cantidad: Mapped[int] = mapped_column(Integer)
    estado: Mapped[str] = mapped_column(String(20))
    vence_en: Mapped[datetime] = mapped_column(DateTime(timezone=True))
    # Copias de lo que respondió eventos: así la reserva no depende de consultarlo otra vez.
    evento_id: Mapped[uuid.UUID | None] = mapped_column(UUID(as_uuid=True))
    evento_nombre: Mapped[str | None] = mapped_column(String(160))
    sector_nombre: Mapped[str | None] = mapped_column(String(80))
    monto_clp: Mapped[int | None] = mapped_column(Integer)
    # Lo necesario para reenviar un paso si su mensaje se pierde.
    resultado_simulado: Mapped[str | None] = mapped_column(String(10))
    transicion_en: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    entradas_emitidas: Mapped[bool] = mapped_column(Boolean, default=False, server_default=false())
    liberacion_pendiente: Mapped[bool] = mapped_column(
        Boolean, default=False, server_default=false()
    )
    creada_en: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
