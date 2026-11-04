"""Errores que cruzan de un servicio a otro."""


class ErrorDeNegocio(Exception):
    """Error esperado que se le puede contar al usuario, por ejemplo "no quedan cupos"."""

    def __init__(self, codigo: str, mensaje: str) -> None:
        super().__init__(mensaje)
        self.codigo = codigo
        self.mensaje = mensaje


class SinRespuesta(Exception):
    """El servicio no respondió a tiempo. La acción pudo haberse ejecutado o no."""


def exigir_rol(identidad: dict | None, *roles: str) -> dict:
    """Devuelve la identidad si tiene uno de los roles; si no, corta con el error adecuado."""
    if identidad is None:
        raise ErrorDeNegocio("no_autorizado", "Debes iniciar sesión")
    if identidad["rol"] not in roles:
        raise ErrorDeNegocio("prohibido", "No tienes permiso para esta acción")
    return identidad
