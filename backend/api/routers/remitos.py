"""Endpoints: seguimiento y operación de remitos (trazabilidad)."""

from typing import Literal, Optional

from fastapi import APIRouter, Depends

from api import serializadores as ser
from api.dependencias import obtener_consultas, servicio
from api.esquemas import OperacionRemitoIn
from domain.enums import TipoRemito
from services.logistica_service import LogisticaService

router = APIRouter(prefix="/api/remitos", tags=["Remitos"])
Servicio = Depends(servicio(LogisticaService))

Operacion = Literal["empaquetar", "despachar", "registrar_checkpoint",
                    "recibir", "reportar_incidencia", "resolver_incidencia",
                    "declarar_extravio", "cancelar"]


@router.get("")
def listar(estado: Optional[str] = None, sede_id: Optional[int] = None,
           tipo: Optional[TipoRemito] = None, en_curso: bool = False,
           consultas=Depends(obtener_consultas)):
    return consultas.remitos(estado, sede_id, tipo.value if tipo else None,
                             en_curso)


@router.get("/{remito_id}")
def obtener(remito_id: int, svc: LogisticaService = Servicio):
    """Remito con su historial completo y las acciones válidas."""
    return ser.remito(svc.obtener(remito_id), svc.uow)


@router.post("/{remito_id}/acciones/{operacion}")
def operar(remito_id: int, operacion: Operacion,
           datos: Optional[OperacionRemitoIn] = None,
           svc: LogisticaService = Servicio):
    """
    Ejecuta una operación del ciclo de vida. Si no es válida para el estado
    actual responde 409 (la decide el patrón State en el dominio).
    """
    datos = datos or OperacionRemitoIn()
    remito = svc.operar(remito_id, operacion, **datos.model_dump())
    return ser.remito(remito, svc.uow)
