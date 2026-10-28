"""Conversión de entidades del dominio a diccionarios JSON."""

from datetime import date, datetime
from enum import Enum


def _valor(v):
    if isinstance(v, Enum):
        return v.value
    if isinstance(v, (date, datetime)):
        return v.isoformat()
    return v


def _campos(entidad, *nombres):
    return {n: _valor(getattr(entidad, n)) for n in nombres}


def sede(s):
    datos = _campos(s, "id", "nombre", "telefono", "email", "activa")
    datos.update(direccion=s.direccion.a_dict(),
                 direccion_texto=s.direccion.texto,
                 horario=s.horario.a_lista(),
                 horario_texto=s.horario.texto)
    return datos


def socio(s):
    return _campos(s, "id", "nombre", "apellido", "nombre_completo",
                   "documento", "email", "telefono", "fecha_alta",
                   "habilitado", "motivo_inhabilitacion")


def libro(l):
    return _campos(l, "isbn", "titulo", "autor", "editorial",
                   "anio_publicacion", "genero")


def ejemplar(e):
    return _campos(e, "id", "isbn", "sede_id", "sede_actual_id",
                   "codigo_inventario", "estado", "condicion")


def prestamo(p):
    return _campos(p, "id", "socio_id", "ejemplar_id", "sede_origen_id",
                   "sede_destino_id", "tipo", "estado", "fecha_solicitud",
                   "dias_prestamo", "fecha_inicio", "fecha_vencimiento",
                   "fecha_devolucion", "condicion_devolucion", "multa",
                   "observaciones", "reserva_id")


def reserva(r):
    return _campos(r, "id", "socio_id", "isbn", "sede_id", "fecha_reserva",
                   "estado", "ejemplar_id", "fecha_limite_retiro")


def remito(r, uow=None):
    datos = _campos(r, "id", "numero", "ejemplar_id", "sede_origen_id",
                    "sede_destino_id", "tipo", "prestamo_id", "estado",
                    "fecha_creacion", "finalizado", "acciones_disponibles",
                    "tuvo_incidencias")
    datos["historial"] = [
        {k: _valor(v) for k, v in m.__dict__.items()} for m in r.historial]
    if uow is not None:
        ej = uow.ejemplares.obtener(r.ejemplar_id)
        datos.update(
            codigo_inventario=ej.codigo_inventario,
            titulo=uow.libros.obtener(ej.isbn).titulo,
            sede_origen=uow.sedes.obtener(r.sede_origen_id).nombre,
            sede_destino=uow.sedes.obtener(r.sede_destino_id).nombre)
    return datos


def notificacion(n):
    return _campos(n, "id", "socio_id", "mensaje", "fecha_hora", "leida")
