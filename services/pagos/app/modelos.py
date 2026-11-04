import uuid
from datetime import datetime

from sqlalchemy import CheckConstraint, DateTime, Integer, String, UniqueConstraint, func
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column


class Base(DeclarativeBase):
    pass


class Pago(Base):
    __tablename__ = "pagos"
    __table_args__ = (
        # Un solo pago por reserva: es lo que hace seguro repetir el procesamiento.
        UniqueConstraint("reserva_id", name="pagos_reserva_id_key"),
        CheckConstraint("estado IN ('APROBADO', 'RECHAZADO')", name="estado_valido"),
    )

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    reserva_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True))
    monto_clp: Mapped[int] = mapped_column(Integer)
    estado: Mapped[str] = mapped_column(String(20))
    creado_en: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
