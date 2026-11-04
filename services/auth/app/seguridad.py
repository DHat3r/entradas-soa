"""Contraseñas y tokens."""

from datetime import UTC, datetime, timedelta

import jwt
from argon2 import PasswordHasher
from argon2.exceptions import InvalidHashError, VerificationError

from app.modelos import Usuario

DURACION_TOKEN = timedelta(hours=8)

_hasher = PasswordHasher()
# Se verifica contra este hash si el correo no existe, para que ambos casos tarden lo mismo
# y no se pueda averiguar qué correos están registrados midiendo el tiempo de respuesta.
_HASH_SEÑUELO = _hasher.hash("contraseña-que-nadie-usa")


def hashear(password: str) -> str:
    return _hasher.hash(password)


def verificar(password: str, password_hash: str | None) -> bool:
    try:
        _hasher.verify(password_hash or _HASH_SEÑUELO, password)
    except (VerificationError, InvalidHashError):
        return False
    return password_hash is not None


def emitir_token(usuario: Usuario, secreto: str) -> str:
    ahora = datetime.now(UTC)
    claims = {
        "sub": str(usuario.id),
        "rol": usuario.rol,
        "correo": usuario.correo,
        "nombre": usuario.nombre,
        "iat": ahora,
        "exp": ahora + DURACION_TOKEN,
    }
    return jwt.encode(claims, secreto, algorithm="HS256")
