import asyncio

from basedatos import Sesiones
from mensajeria import ErrorDeNegocio
from pydantic import BaseModel, EmailStr, Field
from sqlalchemy import select
from sqlalchemy.exc import IntegrityError

from app.modelos import Usuario
from app.seguridad import emitir_token, hashear, verificar


class Registro(BaseModel):
    nombre: str = Field(min_length=2, max_length=120)
    correo: EmailStr
    # Tope para que nadie haga trabajar a argon2 con una contraseña gigante.
    password: str = Field(min_length=8, max_length=128)


class Login(BaseModel):
    correo: EmailStr
    password: str = Field(max_length=128)


def a_dict(usuario: Usuario) -> dict:
    return {
        "id": str(usuario.id),
        "nombre": usuario.nombre,
        "correo": usuario.correo,
        "rol": usuario.rol,
    }


def registrar_acciones(bus, sesiones: Sesiones, jwt_secret: str) -> None:
    @bus.accion("registrar")
    async def registrar(datos: dict, identidad) -> dict:
        registro = Registro(**datos)
        # El rol está fijo: los datos del cliente nunca deciden permisos.
        usuario = Usuario(
            nombre=registro.nombre.strip(),
            correo=registro.correo.lower(),
            # En un hilo aparte: argon2 tarda a propósito y no debe frenar a los demás pedidos.
            password_hash=await asyncio.to_thread(hashear, registro.password),
            rol="cliente",
        )
        async with sesiones() as sesion:
            sesion.add(usuario)
            try:
                await sesion.commit()
            except IntegrityError as error:
                raise ErrorDeNegocio("conflicto", "Ese correo ya está registrado") from error
        return a_dict(usuario)

    @bus.accion("login")
    async def login(datos: dict, identidad) -> dict:
        credenciales = Login(**datos)
        async with sesiones() as sesion:
            usuario = await sesion.scalar(
                select(Usuario).where(Usuario.correo == credenciales.correo.lower())
            )
        hash_guardado = usuario.password_hash if usuario else None
        if not await asyncio.to_thread(verificar, credenciales.password, hash_guardado):
            raise ErrorDeNegocio("no_autorizado", "Correo o contraseña incorrectos")
        return {"token": emitir_token(usuario, jwt_secret), "usuario": a_dict(usuario)}


async def sembrar_internos(sesiones: Sesiones, cuentas: list[tuple[str, str, str, str]]) -> None:
    """Crea las cuentas internas si no existen. Es la única forma de obtener esos roles."""
    async with sesiones() as sesion:
        for nombre, correo, password, rol in cuentas:
            correo = correo.lower()
            existe = await sesion.scalar(select(Usuario.id).where(Usuario.correo == correo))
            if not existe:
                sesion.add(
                    Usuario(nombre=nombre, correo=correo, password_hash=hashear(password), rol=rol)
                )
        await sesion.commit()
