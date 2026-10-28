"""Endpoints: préstamos locales e interbibliotecarios y devoluciones."""

from typing import Optional

from fastapi import APIRouter, Depends

from api import serializadores as ser
from api.dependencias import obtener_consultas, reloj, servicio
from api.esquemas import CancelacionIn, DevolucionIn, PrestamoIn
from domain.enums import EstadoPrestamo, TipoPrestamo
from services.prestamo_service import PrestamoService

router = APIRouter(prefix="/api/prestamos", tags=["Préstamos"])
Servicio = Depends(servicio(PrestamoService))


@router.get("")
def listar(estado: Optional[EstadoPrestamo] = None,
           socio_id: Optional[int] = None, sede_id: Optional[int] = None,
           tipo: Optional[TipoPrestamo] = None, vencidos: bool = False,
           consultas=Depends(obtener_consultas)):
    return consultas.prestamos(
        reloj.hoy(), estado.value if estado else None, socio_id, sede_id,
        tipo.value if tipo else None, vencidos)


@router.get("/elegibilidad/{socio_id}")
def elegibilidad(socio_id: int, svc: PrestamoService = Servicio):
    """Chequeo anticipado: ¿el socio puede pedir un préstamo ahora?"""
    return svc.evaluar_elegibilidad(socio_id)


@router.get("/{prestamo_id}")
def obtener(prestamo_id: int, svc: PrestamoService = Servicio):
    prestamo = svc.obtener(prestamo_id)
    datos = ser.prestamo(prestamo)
    datos["remitos"] = [ser.remito(r)
                        for r in svc.uow.remitos.de_prestamo(prestamo_id)]
    return datos


@router.post("", status_code=201)
def solicitar(datos: PrestamoIn, svc: PrestamoService = Servicio):
    """
    Registra la solicitud. Si origen y destino coinciden es un préstamo
    local (queda ACTIVO); si no, es interbibliotecario y se genera el remito
    de envío.
    """
    return ser.prestamo(svc.solicitar(**datos.model_dump()))


@router.post("/{prestamo_id}/entregar")
def entregar(prestamo_id: int, svc: PrestamoService = Servicio):
    return ser.prestamo(svc.entregar(prestamo_id))


@router.post("/{prestamo_id}/devolucion")
def devolver(prestamo_id: int, datos: DevolucionIn,
             svc: PrestamoService = Servicio):
    return ser.prestamo(svc.registrar_devolucion(
        prestamo_id, datos.condicion, datos.observaciones))


@router.post("/{prestamo_id}/cancelar")
def cancelar(prestamo_id: int, datos: CancelacionIn,
             svc: PrestamoService = Servicio):
    return ser.prestamo(svc.cancelar(prestamo_id, datos.motivo))
