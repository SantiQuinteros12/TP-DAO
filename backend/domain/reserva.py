"""Entidad Reserva: un socio reserva un libro para retirarlo en una sede."""

from datetime import timedelta

from domain.enums import EstadoReserva
from domain.excepciones import TransicionInvalidaError

R = EstadoReserva
DIAS_PARA_RETIRAR = 3


class Reserva:
    """
    Reserva sobre un libro (no sobre un ejemplar puntual).

    Ciclo de vida:
        PENDIENTE  -> DISPONIBLE (se le asigna un ejemplar)
        DISPONIBLE -> CUMPLIDA (se concreta el préstamo) | VENCIDA
        PENDIENTE / DISPONIBLE -> CANCELADA
    """

    def __init__(self, socio_id, isbn, sede_id, fecha_reserva,
                 estado=EstadoReserva.PENDIENTE, ejemplar_id=None,
                 fecha_limite_retiro=None, id=None):
        self.id = id
        self.socio_id = socio_id
        self.isbn = isbn
        self.sede_id = sede_id
        self.fecha_reserva = fecha_reserva
        self._estado = EstadoReserva(estado)
        self.ejemplar_id = ejemplar_id
        self.fecha_limite_retiro = fecha_limite_retiro

    @property
    def estado(self):
        return self._estado

    @property
    def esta_activa(self):
        return self._estado in (R.PENDIENTE, R.DISPONIBLE)

    def _exigir_estado(self, *permitidos):
        if self._estado not in permitidos:
            raise TransicionInvalidaError(
                f"La reserva #{self.id} está en estado {self._estado.value}")

    def asignar_ejemplar(self, ejemplar_id, hoy):
        self._exigir_estado(R.PENDIENTE)
        self.ejemplar_id = ejemplar_id
        self.fecha_limite_retiro = hoy + timedelta(days=DIAS_PARA_RETIRAR)
        self._estado = R.DISPONIBLE

    def cumplir(self, hoy):
        self._exigir_estado(R.DISPONIBLE)
        if self.expiro(hoy):
            raise TransicionInvalidaError(
                "El plazo para retirar la reserva ya venció")
        self._estado = R.CUMPLIDA

    def cancelar(self):
        self._exigir_estado(R.PENDIENTE, R.DISPONIBLE)
        self._estado = R.CANCELADA

    def expiro(self, hoy):
        return (self._estado == R.DISPONIBLE
                and self.fecha_limite_retiro is not None
                and hoy > self.fecha_limite_retiro)

    def vencer(self):
        self._exigir_estado(R.DISPONIBLE)
        self._estado = R.VENCIDA
