import uuid
from datetime import datetime

from sqlalchemy import DateTime, String, func
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column


class Base(DeclarativeBase):
    pass


class CorreoEnviado(Base):
    __tablename__ = "correos_enviados"

    # La reserva es la clave: así un mismo evento no envía el correo dos veces.
    reserva_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True)
    destinatario: Mapped[str] = mapped_column(String(254))
    enviado_en: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
