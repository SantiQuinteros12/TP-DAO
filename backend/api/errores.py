"""Traducción de excepciones del dominio a respuestas HTTP."""

from fastapi import Request
from fastapi.responses import JSONResponse

from domain.excepciones import (DatoInvalidoError, DuplicadoError,
                                EntidadNoEncontradaError, ErrorDominio,
                                ReglaNegocioError, TransicionInvalidaError)

# Ordenado de más específico a más general.
CODIGOS_HTTP = (
    (EntidadNoEncontradaError, 404),
    (DuplicadoError, 409),
    (TransicionInvalidaError, 409),
    (ReglaNegocioError, 422),
    (DatoInvalidoError, 400),
)


def manejar_error_dominio(request: Request, exc: ErrorDominio):
    codigo = next((c for tipo, c in CODIGOS_HTTP if isinstance(exc, tipo)),
                  400)
    return JSONResponse(status_code=codigo,
                        content={"detail": exc.mensaje,
                                 "tipo": type(exc).__name__})


def registrar(app):
    app.add_exception_handler(ErrorDominio, manejar_error_dominio)
