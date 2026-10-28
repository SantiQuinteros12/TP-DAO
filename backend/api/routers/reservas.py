"""Endpoints: gestión de reservas."""

from typing import Optional

from fastapi import APIRouter, Depends

from api import serializadores as ser
from api.dependencias import obtener_consultas, servicio
from api.esquemas import ReservaIn
from domain.enums import EstadoReserva
from services.prestamo_service import PrestamoService
from services.reserva_service import ReservaService

router = APIRouter(prefix="/api/reservas", tags=["Reservas"])
Servicio = Depends(servicio(ReservaService))


@router.get("")
def listar(estado: Optional[EstadoReserva] = None,
           socio_id: Optional[int] = None, sede_id: Optional[int] = None,
           consultas=Depends(obtener_consultas)):
    return consultas.reservas(estado.value if estado else None, socio_id,
                              sede_id)


@router.post("", status_code=201)
def crear(datos: ReservaIn, svc: ReservaService = Servicio):
    return ser.reserva(svc.crear(**datos.model_dump()))


@router.post("/{reserva_id}/cancelar")
def cancelar(reserva_id: int, svc: ReservaService = Servicio):
    return ser.reserva(svc.cancelar(reserva_id))


@router.post("/{reserva_id}/concretar", status_code=201)
def concretar(reserva_id: int,
              svc: PrestamoService = Depends(servicio(PrestamoService))):
    """Convierte la reserva disponible en un préstamo local."""
    return ser.prestamo(svc.concretar_reserva(reserva_id))


@router.post("/procesar-vencimientos")
def procesar_vencimientos(svc: ReservaService = Servicio):
    return {"reservas_vencidas": svc.procesar_vencidas()}
