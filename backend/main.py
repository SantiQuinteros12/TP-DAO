"""
Punto de entrada de la API REST.

Ejecutar desde la carpeta ``backend``::

    uvicorn main:app --reload

Documentación interactiva: http://localhost:8000/docs
"""

from contextlib import asynccontextmanager
from pathlib import Path

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

import config
from api import errores
from api.routers import (catalogo, prestamos, remitos, reportes, reservas,
                         sedes, socios)
from infrastructure.database import inicializar_esquema


@asynccontextmanager
async def ciclo_de_vida(app):
    Path(config.RUTA_DB).parent.mkdir(parents=True, exist_ok=True)
    inicializar_esquema(config.RUTA_DB)
    yield


def crear_app():
    app = FastAPI(
        title="Red de Bibliotecas - Préstamos Interbibliotecarios",
        description="API REST del TPI de Desarrollo de Aplicaciones con "
                    "Objetos (UTN FRC).",
        version="1.0.0",
        lifespan=ciclo_de_vida,
    )
    app.add_middleware(CORSMiddleware, allow_origins=config.ORIGENES_CORS,
                       allow_methods=["*"], allow_headers=["*"])
    errores.registrar(app)
    for modulo in (sedes, socios, catalogo, prestamos, reservas, remitos,
                   reportes):
        app.include_router(modulo.router)
    return app


app = crear_app()
