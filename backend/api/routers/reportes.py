"""Endpoints: reportes de gestión."""

from datetime import date
from typing import Optional

from fastapi import APIRouter, Depends, Query

from api.dependencias import obtener_reportes
from services.reporte_service import ReporteService

router = APIRouter(prefix="/api/reportes", tags=["Reportes"])
Reportes = Depends(obtener_reportes)


@router.get("/resumen")
def resumen(svc: ReporteService = Reportes):
    return svc.resumen()


@router.get("/prestamos-activos")
def prestamos_activos_y_transito(svc: ReporteService = Reportes):
    return svc.prestamos_activos_y_transito()


@router.get("/vencidos")
def vencidos_y_multas(svc: ReporteService = Reportes):
    return svc.vencidos_y_multas()


@router.get("/libros-mas-solicitados")
def libros_mas_solicitados(desde: Optional[date] = None,
                           hasta: Optional[date] = None,
                           limite: int = Query(10, ge=1, le=100),
                           svc: ReporteService = Reportes):
    return svc.libros_mas_solicitados(desde, hasta, limite)


@router.get("/disponibilidad-sedes")
def disponibilidad_por_sede(svc: ReporteService = Reportes):
    return svc.disponibilidad_por_sede()


@router.get("/logistica")
def logistica(desde: Optional[date] = None, hasta: Optional[date] = None,
              svc: ReporteService = Reportes):
    return svc.logistica(desde, hasta)


@router.get("/tendencias")
def tendencias(desde: Optional[date] = None, hasta: Optional[date] = None,
               svc: ReporteService = Reportes):
    return svc.tendencias(desde, hasta)
