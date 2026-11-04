"""Arma el correo con las entradas como PNG adjuntos y lo envía por SMTP."""

import html
import uuid
from email.message import EmailMessage
from io import BytesIO

import aiosmtplib
import segno
from pydantic import BaseModel


class EntradaEmitida(BaseModel):
    id: uuid.UUID
    codigo: str


class DatosDeEntradas(BaseModel):
    """Datos de entradas.emitidas que necesita el correo."""

    reserva_id: uuid.UUID
    cliente_correo: str
    evento_nombre: str
    sector_nombre: str
    entradas: list[EntradaEmitida]


def construir_correo(remitente: str, datos: DatosDeEntradas) -> EmailMessage:
    cantidad = len(datos.entradas)
    mensaje = EmailMessage()
    mensaje["To"] = datos.cliente_correo
    mensaje["From"] = remitente
    # Un salto de línea en el asunto haría fallar el envío y la entrada nunca llegaría.
    nombre_en_una_linea = " ".join(datos.evento_nombre.split())
    mensaje["Subject"] = f"Tus entradas para {nombre_en_una_linea}"
    mensaje.set_content(
        f"Tienes {cantidad} entrada(s) para {datos.evento_nombre}, sector {datos.sector_nombre}.\n"
        "Adjuntamos un código QR por entrada. Preséntalo en el acceso.\n"
    )
    # El nombre del evento lo escribe un organizador: se escapa antes de ir al HTML.
    evento = html.escape(datos.evento_nombre)
    sector = html.escape(datos.sector_nombre)
    mensaje.add_alternative(
        f"<p>Tienes {cantidad} entrada(s) para <strong>{evento}</strong>, sector {sector}.</p>"
        "<p>Adjuntamos un código QR por entrada. Preséntalo en el acceso.</p>",
        subtype="html",
    )
    for numero, entrada in enumerate(datos.entradas, start=1):
        png = BytesIO()
        segno.make(entrada.codigo, error="m").save(png, kind="png", scale=8)
        mensaje.add_attachment(
            png.getvalue(),
            maintype="image",
            subtype="png",
            filename=f"entrada-{numero}.png",
        )
    return mensaje


class EnviadorSmtp:
    def __init__(self, host: str, puerto: int) -> None:
        self.host = host
        self.puerto = puerto

    async def enviar(self, mensaje: EmailMessage) -> None:
        # Sin TLS ni autenticación porque Mailpit es local. Con un SMTP real habría que agregarlos.
        await aiosmtplib.send(
            mensaje,
            hostname=self.host,
            port=self.puerto,
            timeout=10,
        )
