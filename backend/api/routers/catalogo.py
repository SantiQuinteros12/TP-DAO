"""Endpoints: catálogo de libros, ejemplares y disponibilidad."""

from typing import Optional

from fastapi import APIRouter, Depends

from api import serializadores as ser
from api.dependencias import obtener_consultas, servicio
from api.esquemas import EjemplarIn, LibroDatos, LibroIn, TrasladoIn
from domain.enums import EstadoEjemplar
from domain.libro import ISBN
from services.catalogo_service import CatalogoService
from services.logistica_service import LogisticaService

router = APIRouter(prefix="/api", tags=["Catálogo"])
Catalogo = Depends(servicio(CatalogoService))
Consultas = Depends(obtener_consultas)


# --- libros --------------------------------------------------------------
@router.get("/libros")
def listar_libros(q: Optional[str] = None, svc: CatalogoService = Catalogo):
    return [ser.libro(l) for l in svc.listar_libros(q)]


@router.get("/libros/{isbn}")
def obtener_libro(isbn: str, svc: CatalogoService = Catalogo):
    return ser.libro(svc.obtener_libro(isbn))


@router.post("/libros", status_code=201)
def crear_libro(datos: LibroIn, svc: CatalogoService = Catalogo):
    return ser.libro(svc.crear_libro(**datos.model_dump()))


@router.put("/libros/{isbn}")
def actualizar_libro(isbn: str, datos: LibroDatos,
                     svc: CatalogoService = Catalogo):
    return ser.libro(svc.actualizar_libro(isbn, **datos.model_dump()))


# --- ejemplares ----------------------------------------------------------
@router.get("/ejemplares")
def listar_ejemplares(isbn: Optional[str] = None,
                      sede_id: Optional[int] = None,
                      estado: Optional[EstadoEjemplar] = None,
                      q: Optional[str] = None, consultas=Consultas):
    isbn = ISBN(isbn).valor if isbn else None
    return consultas.ejemplares(isbn, sede_id,
                                estado.value if estado else None, q)


@router.post("/ejemplares", status_code=201)
def crear_ejemplar(datos: EjemplarIn, svc: CatalogoService = Catalogo):
    return ser.ejemplar(svc.crear_ejemplar(**datos.model_dump()))


@router.post("/ejemplares/{ejemplar_id}/baja")
def baja_ejemplar(ejemplar_id: int, svc: CatalogoService = Catalogo):
    return ser.ejemplar(svc.dar_de_baja_ejemplar(ejemplar_id))


@router.post("/ejemplares/{ejemplar_id}/reparar")
def reparar_ejemplar(ejemplar_id: int, svc: CatalogoService = Catalogo):
    return ser.ejemplar(svc.reparar_ejemplar(ejemplar_id))


@router.post("/ejemplares/{ejemplar_id}/traslado", status_code=201)
def trasladar_ejemplar(ejemplar_id: int, datos: TrasladoIn,
                       svc: LogisticaService = Depends(
                           servicio(LogisticaService))):
    """Reasigna el ejemplar a otra sede generando un remito de TRASLADO."""
    remito = svc.trasladar_ejemplar(ejemplar_id, datos.sede_destino_id)
    return ser.remito(remito, svc.uow)


# --- disponibilidad ------------------------------------------------------
@router.get("/disponibilidad")
def disponibilidad(isbn: Optional[str] = None, sede_id: Optional[int] = None,
                   q: Optional[str] = None, consultas=Consultas):
    """Ejemplares por estado para cada combinación libro / sede."""
    isbn = ISBN(isbn).valor if isbn else None
    return consultas.disponibilidad(isbn, sede_id, q)
