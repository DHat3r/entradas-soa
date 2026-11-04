"""Códigos del QR: el id de la entrada más una firma que solo este servicio puede generar."""

import base64
import hashlib
import hmac
import uuid

import segno


def _firma(entrada_id: uuid.UUID, secreto: str) -> str:
    digest = hmac.new(secreto.encode(), entrada_id.bytes, hashlib.sha256).digest()
    return base64.urlsafe_b64encode(digest).rstrip(b"=").decode()


def generar_codigo(entrada_id: uuid.UUID, secreto: str) -> str:
    return f"{entrada_id}.{_firma(entrada_id, secreto)}"


def leer_codigo(codigo: str, secreto: str) -> uuid.UUID | None:
    """Devuelve el id si la firma es válida. Un código alterado ni siquiera llega a la base."""
    id_texto, separador, firma = codigo.partition(".")
    if not separador:
        return None
    try:
        entrada_id = uuid.UUID(id_texto)
    except ValueError:
        return None
    # compare_digest tarda lo mismo sin importar dónde difieran: no filtra la firma por tiempo.
    if not hmac.compare_digest(firma.encode(), _firma(entrada_id, secreto).encode()):
        return None
    return entrada_id


def qr_como_data_uri(codigo: str) -> str:
    return segno.make(codigo, error="m").svg_data_uri(scale=6, border=2)
