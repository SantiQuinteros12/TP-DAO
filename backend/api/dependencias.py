"""
Inyección de dependencias de FastAPI.

Cada request obtiene su propia Unidad de Trabajo: si el endpoint termina
bien se confirma la transacción; ante cualquier excepción se revierte, de
modo que un caso de uso nunca deja la base a medio actualizar.
"""

from fastapi import Depends

import config
from domain.reloj import RelojSistema
from infrastructure.consultas_sqlite import ConsultasSQLite
from infrastructure.repositorios_sqlite import UnidadDeTrabajoSQLite
from services.notificaciones import crear_publicador
from services.reporte_service import ReporteService

reloj = RelojSistema()
publicador = crear_publicador()


def obtener_uow():
    uow = UnidadDeTrabajoSQLite(config.RUTA_DB)
    try:
        yield uow
        uow.confirmar()
    except Exception:
        uow.revertir()
        raise
    finally:
        uow.cerrar()


def servicio(clase):
    """Crea una dependencia que construye el servicio ``clase``."""

    def construir(uow=Depends(obtener_uow)):
        return clase(uow, reloj, publicador)

    return construir


def obtener_consultas(uow=Depends(obtener_uow)):
    return ConsultasSQLite(uow.conexion)


def obtener_reportes(consultas=Depends(obtener_consultas)):
    return ReporteService(consultas, reloj)
