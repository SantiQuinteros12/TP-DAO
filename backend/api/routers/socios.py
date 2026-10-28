"""Endpoints: administración de socios y sus notificaciones."""

from typing import Optional

from fastapi import APIRouter, Depends

from api import serializadores as ser
from api.dependencias import servicio
from api.esquemas import InhabilitacionIn, SocioIn
from services.socio_service import SocioService

router = APIRouter(prefix="/api/socios", tags=["Socios"])
Servicio = Depends(servicio(SocioService))


@router.get("")
def listar(q: Optional[str] = None, habilitado: Optional[bool] = None,
           svc: SocioService = Servicio):
    return [ser.socio(s) for s in svc.listar(q, habilitado)]


@router.get("/{socio_id}")
def obtener(socio_id: int, svc: SocioService = Servicio):
    return ser.socio(svc.obtener(socio_id))


@router.post("", status_code=201)
def crear(datos: SocioIn, svc: SocioService = Servicio):
    return ser.socio(svc.crear(**datos.model_dump()))


@router.put("/{socio_id}")
def actualizar(socio_id: int, datos: SocioIn, svc: SocioService = Servicio):
    return ser.socio(svc.actualizar(socio_id, **datos.model_dump()))


@router.post("/{socio_id}/inhabilitar")
def inhabilitar(socio_id: int, datos: InhabilitacionIn,
                svc: SocioService = Servicio):
    return ser.socio(svc.inhabilitar(socio_id, datos.motivo))


@router.post("/{socio_id}/habilitar")
def habilitar(socio_id: int, svc: SocioService = Servicio):
    return ser.socio(svc.habilitar(socio_id))


@router.get("/{socio_id}/notificaciones")
def notificaciones(socio_id: int, solo_no_leidas: bool = False,
                   svc: SocioService = Servicio):
    return [ser.notificacion(n)
            for n in svc.notificaciones(socio_id, solo_no_leidas)]


@router.post("/{socio_id}/notificaciones/leidas", status_code=204)
def marcar_leidas(socio_id: int, svc: SocioService = Servicio):
    svc.marcar_notificaciones_leidas(socio_id)
