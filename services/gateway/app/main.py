"""Única puerta HTTP. Lee la sesión, traduce a mensajes y deja las reglas a cada servicio."""

import os
import time
from collections import defaultdict
from contextlib import asynccontextmanager
from dataclasses import dataclass

import jwt
from fastapi import Body, Depends, FastAPI, Request, Response
from fastapi.responses import JSONResponse
from mensajeria import Bus, ErrorDeNegocio, SinRespuesta

COOKIE_SESION = "sesion"
DURACION_COOKIE_SEGUNDOS = 8 * 60 * 60
MAX_INTENTOS_LOGIN = 5
VENTANA_LOGIN_SEGUNDOS = 60

HTTP_POR_CODIGO = {
    "validacion": 422,
    "no_autorizado": 401,
    "prohibido": 403,
    "no_encontrado": 404,
    "conflicto": 409,
}


@dataclass
class Ajustes:
    jwt_secret: str
    cookie_secure: bool = True


class LimitadorDeLogin:
    """Ventana deslizante por IP. Vive en memoria: vale por instancia del gateway."""

    def __init__(self, ahora=time.monotonic) -> None:
        self._ahora = ahora
        self._intentos: dict[str, list[float]] = defaultdict(list)

    def permitir(self, ip: str) -> bool:
        limite = self._ahora() - VENTANA_LOGIN_SEGUNDOS
        recientes = [t for t in self._intentos[ip] if t > limite]
        permitido = len(recientes) < MAX_INTENTOS_LOGIN
        if permitido:
            recientes.append(self._ahora())
        self._intentos[ip] = recientes
        return permitido


def leer_identidad(request: Request, jwt_secret: str) -> dict | None:
    """Un token ausente, vencido o alterado equivale a no tener sesión."""
    encabezado = request.headers.get("authorization", "")
    token = encabezado[7:] if encabezado.lower().startswith("bearer ") else None
    token = token or request.cookies.get(COOKIE_SESION)
    if not token:
        return None
    try:
        claims = jwt.decode(token, jwt_secret, algorithms=["HS256"])
    except jwt.PyJWTError:
        return None
    return {
        "usuario_id": claims["sub"],
        "rol": claims["rol"],
        "correo": claims["correo"],
        "nombre": claims["nombre"],
    }


def crear_app(bus, ajustes: Ajustes, conectar_bus: bool = True) -> FastAPI:
    @asynccontextmanager
    async def ciclo_de_vida(app: FastAPI):
        if conectar_bus:
            await bus.conectar()
        yield
        if conectar_bus:
            await bus.cerrar()

    app = FastAPI(
        title="Entradas SOA",
        version="1.0.0",
        lifespan=ciclo_de_vida,
        docs_url="/api/docs",
        openapi_url="/api/openapi.json",
    )
    limitador = LimitadorDeLogin()

    @app.exception_handler(ErrorDeNegocio)
    async def error_de_negocio(request: Request, error: ErrorDeNegocio) -> JSONResponse:
        estado = HTTP_POR_CODIGO.get(error.codigo, 500)
        return JSONResponse({"codigo": error.codigo, "mensaje": error.mensaje}, status_code=estado)

    @app.exception_handler(SinRespuesta)
    async def sin_respuesta(request: Request, error: SinRespuesta) -> JSONResponse:
        return JSONResponse(
            {"codigo": "sin_respuesta", "mensaje": "El servicio no respondió, intenta de nuevo"},
            status_code=504,
        )

    def identidad(request: Request) -> dict | None:
        return leer_identidad(request, ajustes.jwt_secret)

    @app.get("/api/health")
    async def health() -> dict:
        return {"estado": "ok"}

    # ── Sesión ───────────────────────────────────────────────────────────────
    @app.post("/api/auth/registro", status_code=201)
    async def registro(datos: dict = Body(...)):
        return await bus.pedir("auth", "registrar", datos)

    @app.post("/api/auth/login")
    async def login(request: Request, response: Response, datos: dict = Body(...)):
        ip = request.client.host if request.client else "desconocida"
        if not limitador.permitir(ip):
            return JSONResponse(
                {"codigo": "demasiados_intentos", "mensaje": "Espera un minuto e intenta de nuevo"},
                status_code=429,
            )
        resultado = await bus.pedir("auth", "login", datos)
        response.set_cookie(
            COOKIE_SESION,
            resultado["token"],
            max_age=DURACION_COOKIE_SEGUNDOS,
            httponly=True,
            samesite="strict",
            secure=ajustes.cookie_secure,
            path="/",
        )
        return resultado

    @app.post("/api/auth/logout", status_code=204)
    async def logout(response: Response) -> None:
        response.delete_cookie(COOKIE_SESION, path="/")

    @app.get("/api/auth/yo")
    async def yo(quien: dict | None = Depends(identidad)):
        if quien is None:
            raise ErrorDeNegocio("no_autorizado", "Debes iniciar sesión")
        return quien

    # ── Eventos ──────────────────────────────────────────────────────────────
    @app.get("/api/eventos")
    async def listar_eventos():
        return await bus.pedir("eventos", "listar_publicados")

    @app.get("/api/eventos/{evento_id}")
    async def detalle_evento(evento_id: str, quien: dict | None = Depends(identidad)):
        return await bus.pedir("eventos", "detalle", {"evento_id": evento_id}, quien)

    @app.post("/api/eventos", status_code=201)
    async def crear_evento(datos: dict = Body(...), quien: dict | None = Depends(identidad)):
        return await bus.pedir("eventos", "crear", datos, quien)

    @app.post("/api/eventos/{evento_id}/publicar")
    async def publicar_evento(evento_id: str, quien: dict | None = Depends(identidad)):
        return await bus.pedir("eventos", "publicar", {"evento_id": evento_id}, quien)

    @app.get("/api/interno/eventos")
    async def mis_eventos(quien: dict | None = Depends(identidad)):
        return await bus.pedir("eventos", "listar_mios", identidad=quien)

    # ── Reservas ─────────────────────────────────────────────────────────────
    @app.post("/api/reservas", status_code=201)
    async def crear_reserva(datos: dict = Body(...), quien: dict | None = Depends(identidad)):
        return await bus.pedir("reservas", "crear", datos, quien)

    @app.get("/api/reservas")
    async def mis_reservas(quien: dict | None = Depends(identidad)):
        return await bus.pedir("reservas", "listar_mias", identidad=quien)

    @app.get("/api/reservas/{reserva_id}")
    async def detalle_reserva(reserva_id: str, quien: dict | None = Depends(identidad)):
        return await bus.pedir("reservas", "detalle", {"reserva_id": reserva_id}, quien)

    @app.post("/api/reservas/{reserva_id}/pagar", status_code=202)
    async def pagar_reserva(
        reserva_id: str, datos: dict = Body(...), quien: dict | None = Depends(identidad)
    ):
        return await bus.pedir("reservas", "pagar", {**datos, "reserva_id": reserva_id}, quien)

    # ── Entradas ─────────────────────────────────────────────────────────────
    @app.get("/api/entradas")
    async def mis_entradas(quien: dict | None = Depends(identidad)):
        return await bus.pedir("entradas", "listar_mias", identidad=quien)

    @app.post("/api/entradas/validar")
    async def validar_entrada(datos: dict = Body(...), quien: dict | None = Depends(identidad)):
        return await bus.pedir("entradas", "validar", datos, quien)

    return app


def crear_app_de_produccion() -> FastAPI:
    jwt_secret = os.environ["JWT_SECRET"]
    if len(jwt_secret) < 32:
        raise SystemExit("JWT_SECRET debe tener al menos 32 caracteres")
    ajustes = Ajustes(
        jwt_secret=jwt_secret,
        cookie_secure=os.getenv("COOKIE_SECURE", "true").lower() == "true",
    )
    return crear_app(Bus(os.environ["RABBITMQ_URL"], "gateway"), ajustes)
