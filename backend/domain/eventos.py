"""
Patrón OBSERVER: eventos de dominio.

Las entidades registran eventos al cambiar de estado; los servicios los
publican y los suscriptores (ej. notificaciones a socios) reaccionan sin que
la entidad ni el servicio que la modifica los conozcan (bajo acoplamiento).
"""

from collections import defaultdict
from dataclasses import dataclass
from datetime import datetime


@dataclass(frozen=True)
class EventoDominio:
    ocurrido_en: datetime

    @property
    def nombre(self):
        return type(self).__name__


@dataclass(frozen=True)
class RemitoCambioEstado(EventoDominio):
    remito_id: int
    tipo_remito: str
    prestamo_id: int
    estado_anterior: str
    estado_nuevo: str
    observacion: str = ""


@dataclass(frozen=True)
class ReservaDisponible(EventoDominio):
    reserva_id: int
    socio_id: int
    isbn: str
    sede_id: int


@dataclass(frozen=True)
class PrestamoDevuelto(EventoDominio):
    prestamo_id: int
    socio_id: int
    multa: float = 0.0


class PublicadorEventos:
    """Sujeto observable: mantiene la lista de suscriptores por evento."""

    def __init__(self):
        self._suscriptores = defaultdict(list)

    def suscribir(self, tipo_evento, manejador):
        """
        :param tipo_evento: clase del evento (subclase de EventoDominio)
        :param manejador: callable(evento, uow)
        """
        self._suscriptores[tipo_evento].append(manejador)

    def publicar(self, evento, uow):
        for manejador in self._suscriptores[type(evento)]:
            manejador(evento, uow)

    def publicar_todos(self, eventos, uow):
        for evento in eventos:
            self.publicar(evento, uow)


class RegistroEventos:
    """Mixin para que una entidad acumule eventos pendientes de publicar."""

    def __init__(self):
        self._eventos = []

    def registrar_evento(self, evento):
        self._eventos.append(evento)

    def extraer_eventos(self):
        eventos, self._eventos = self._eventos, []
        return eventos
