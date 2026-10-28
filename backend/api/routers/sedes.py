"""Endpoints: administración de sedes (ABMC)."""

from fastapi import APIRouter, Depends

from api import serializadores as ser
from api.dependencias import servicio
from api.esquemas import SedeIn
from services.sede_service import SedeService

router = APIRouter(prefix="/api/sedes", tags=["Sedes"])
Servicio = Depends(servicio(SedeService))


@router.get("")
def listar(incluir_bajas: bool = True, svc: SedeService = Servicio):
    return [ser.sede(s) for s in svc.listar(incluir_bajas)]


@router.get("/{sede_id}")
def obtener(sede_id: int, svc: SedeService = Servicio):
    return ser.sede(svc.obtener(sede_id))


@router.post("", status_code=201)
def crear(datos: SedeIn, svc: SedeService = Servicio):
    return ser.sede(svc.crear(**datos.model_dump()))


@router.put("/{sede_id}")
def actualizar(sede_id: int, datos: SedeIn, svc: SedeService = Servicio):
    return ser.sede(svc.actualizar(sede_id, **datos.model_dump()))


@router.post("/{sede_id}/baja")
def dar_de_baja(sede_id: int, svc: SedeService = Servicio):
    return ser.sede(svc.dar_de_baja(sede_id))


@router.post("/{sede_id}/reactivar")
def reactivar(sede_id: int, svc: SedeService = Servicio):
    return ser.sede(svc.reactivar(sede_id))
