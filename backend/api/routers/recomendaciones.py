"""Endpoints: recomendaciones de lectura."""

from typing import Optional

from fastapi import APIRouter, Depends, Query

from api.dependencias import obtener_recomendaciones
from services.recomendacion_service import RecomendacionService

router = APIRouter(prefix="/api/recomendaciones", tags=["Recomendaciones"])
Recomendaciones = Depends(obtener_recomendaciones)


@router.get("")
def para_socio(socio_id: Optional[int] = None,
               limite: int = Query(8, ge=1, le=30),
               svc: RecomendacionService = Recomendaciones):
    return svc.para_socio(socio_id, limite)


@router.get("/similares/{isbn}")
def similares(isbn: str, limite: int = Query(6, ge=1, le=30),
              svc: RecomendacionService = Recomendaciones):
    return svc.similares(isbn, limite)
