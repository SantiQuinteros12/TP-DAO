"""
Excepciones del dominio.

Las capas superiores (API) traducen cada tipo a un código HTTP, de modo que
el dominio nunca conoce detalles de transporte.
"""


class ErrorDominio(Exception):
    """Error base del dominio."""

    def __init__(self, mensaje):
        super().__init__(mensaje)
        self.mensaje = mensaje


class EntidadNoEncontradaError(ErrorDominio):
    """La entidad solicitada no existe."""

    def __init__(self, entidad, identificador):
        super().__init__(f"{entidad} '{identificador}' no encontrado/a")
        self.entidad = entidad
        self.identificador = identificador


class DuplicadoError(ErrorDominio):
    """Se intentó registrar una entidad que ya existe."""


class ReglaNegocioError(ErrorDominio):
    """Se violó una regla o validación de negocio."""


class TransicionInvalidaError(ReglaNegocioError):
    """La operación no está permitida en el estado actual de la entidad."""


class DatoInvalidoError(ErrorDominio):
    """Un dato de entrada no cumple el formato esperado."""
