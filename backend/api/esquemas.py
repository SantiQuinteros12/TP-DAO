"""Esquemas Pydantic de entrada (validación sintáctica de los requests)."""

from typing import Optional

from pydantic import BaseModel, Field

from domain.enums import CondicionFisica, TipoIncidencia


class DireccionIn(BaseModel):
    calle: str
    numero: str
    piso_depto: str = ""
    barrio: str = ""
    ciudad: str
    provincia: str
    codigo_postal: str = ""


class FranjaHorariaIn(BaseModel):
    dias: list[int] = Field(min_length=1)
    desde: str
    hasta: str


class SedeIn(BaseModel):
    nombre: str = Field(min_length=1, max_length=80)
    direccion: DireccionIn
    telefono: str = ""
    email: str = ""
    horario: list[FranjaHorariaIn] = []


class SocioIn(BaseModel):
    nombre: str = Field(min_length=1)
    apellido: str = Field(min_length=1)
    documento: str
    email: str = ""
    telefono: str = ""


class InhabilitacionIn(BaseModel):
    motivo: str = Field(min_length=3)


class LibroDatos(BaseModel):
    titulo: str = Field(min_length=1)
    autor: str = Field(min_length=1)
    editorial: str = ""
    anio_publicacion: Optional[int] = None
    genero: str = ""


class LibroIn(LibroDatos):
    isbn: str


class EjemplarIn(BaseModel):
    isbn: str
    sede_id: int
    codigo_inventario: Optional[str] = None


class TrasladoIn(BaseModel):
    sede_destino_id: int


class PrestamoIn(BaseModel):
    socio_id: int
    ejemplar_id: int
    sede_origen_id: int
    sede_destino_id: int


class DevolucionIn(BaseModel):
    condicion: CondicionFisica
    observaciones: str = ""


class CancelacionIn(BaseModel):
    motivo: str = Field(min_length=3)


class ReservaIn(BaseModel):
    socio_id: int
    isbn: str
    sede_id: int


class OperacionRemitoIn(BaseModel):
    responsable: str = ""
    ubicacion: str = ""
    observacion: str = ""
    tipo_incidencia: Optional[TipoIncidencia] = None
    condicion: Optional[CondicionFisica] = None
