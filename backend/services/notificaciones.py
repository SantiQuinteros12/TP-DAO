"""
Suscriptores de eventos (Observer) que generan notificaciones a socios.

Proceso opcional "Envío de notificaciones": hoy se persisten y se consultan
desde la SPA; agregar email/SMS sería sumar otro suscriptor sin tocar los
servicios que originan los eventos.
"""

from domain.eventos import (PrestamoDevuelto, PublicadorEventos,
                            RemitoCambioEstado, ReservaDisponible)
from domain.notificacion import Notificacion

MENSAJES_ENVIO = {
    "DESPACHADO": "Tu pedido de '{titulo}' fue despachado desde {origen}.",
    "RECIBIDO": "'{titulo}' llegó a {destino}: ya podés retirarlo.",
    "CON_INCIDENCIA": "El envío de '{titulo}' registró una incidencia: "
                      "{observacion}",
    "EXTRAVIADO": "Lamentablemente el ejemplar de '{titulo}' se extravió "
                  "durante el envío. Tu préstamo fue cancelado.",
    "CANCELADO": "El envío de '{titulo}' fue cancelado: {observacion}",
}


def _notificar(uow, socio_id, mensaje, fecha_hora):
    uow.notificaciones.guardar(Notificacion(socio_id, mensaje, fecha_hora))


def al_cambiar_remito(evento, uow):
    if evento.tipo_remito != "ENVIO" or not evento.prestamo_id:
        return
    plantilla = MENSAJES_ENVIO.get(evento.estado_nuevo)
    if not plantilla:
        return
    prestamo = uow.prestamos.obtener(evento.prestamo_id)
    ejemplar = uow.ejemplares.obtener(prestamo.ejemplar_id)
    mensaje = plantilla.format(
        titulo=uow.libros.obtener(ejemplar.isbn).titulo,
        origen=uow.sedes.obtener(prestamo.sede_origen_id).nombre,
        destino=uow.sedes.obtener(prestamo.sede_destino_id).nombre,
        observacion=evento.observacion)
    _notificar(uow, prestamo.socio_id, mensaje, evento.ocurrido_en)


def al_quedar_reserva_disponible(evento, uow):
    reserva = uow.reservas.obtener(evento.reserva_id)
    titulo = uow.libros.obtener(evento.isbn).titulo
    sede = uow.sedes.obtener(evento.sede_id).nombre
    _notificar(uow, evento.socio_id,
               f"Tu reserva de '{titulo}' está disponible en {sede}. "
               f"Podés retirarla hasta el {reserva.fecha_limite_retiro:%d/%m/%Y}.",
               evento.ocurrido_en)


def al_devolver_prestamo(evento, uow):
    if evento.multa > 0:
        _notificar(uow, evento.socio_id,
                   f"Se registró una multa de ${evento.multa:,.2f} en la "
                   f"devolución del préstamo #{evento.prestamo_id}.",
                   evento.ocurrido_en)


def crear_publicador():
    """Arma el publicador de eventos con todos los suscriptores."""
    publicador = PublicadorEventos()
    publicador.suscribir(RemitoCambioEstado, al_cambiar_remito)
    publicador.suscribir(ReservaDisponible, al_quedar_reserva_disponible)
    publicador.suscribir(PrestamoDevuelto, al_devolver_prestamo)
    return publicador
