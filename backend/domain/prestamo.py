"""Entidad Prestamo (préstamo local o interbibliotecario)."""

from datetime import timedelta

from domain.enums import CondicionFisica, EstadoPrestamo, TipoPrestamo
from domain.excepciones import TransicionInvalidaError
from domain.multas import politica_para

P = EstadoPrestamo


class Prestamo:
    """
    Préstamo de un ejemplar a un socio.

    Ciclo de vida:
        LOCAL:              ACTIVO -> DEVUELTO
        INTERBIBLIOTECARIO: PENDIENTE_ENVIO -> LISTO_PARA_RETIRO -> ACTIVO
                            -> DEVUELTO
        Cualquier estado previo a ACTIVO puede pasar a CANCELADO.

    :param sede_origen_id: sede propietaria desde la que sale el ejemplar
    :param sede_destino_id: sede donde el socio retira y devuelve
    :param dias_prestamo: plazo otorgado a partir de la entrega
    :param politica_multa: estrategia de cálculo de multas (Strategy)
    """

    def __init__(self, socio_id, ejemplar_id, sede_origen_id, sede_destino_id,
                 fecha_solicitud, dias_prestamo, estado,
                 politica_multa=None, fecha_inicio=None,
                 fecha_vencimiento=None, fecha_devolucion=None,
                 condicion_devolucion=None, multa=0.0, observaciones="",
                 reserva_id=None, id=None):
        self.id = id
        self.socio_id = socio_id
        self.ejemplar_id = ejemplar_id
        self.sede_origen_id = sede_origen_id
        self.sede_destino_id = sede_destino_id
        self.fecha_solicitud = fecha_solicitud
        self.dias_prestamo = dias_prestamo
        self._estado = EstadoPrestamo(estado)
        self.politica_multa = politica_multa or politica_para(self.tipo)
        self.fecha_inicio = fecha_inicio
        self.fecha_vencimiento = fecha_vencimiento
        self.fecha_devolucion = fecha_devolucion
        self.condicion_devolucion = (CondicionFisica(condicion_devolucion)
                                     if condicion_devolucion else None)
        self.multa = multa
        self.observaciones = observaciones
        self.reserva_id = reserva_id

    @property
    def estado(self):
        return self._estado

    @property
    def tipo(self):
        if self.sede_origen_id == self.sede_destino_id:
            return TipoPrestamo.LOCAL
        return TipoPrestamo.INTERBIBLIOTECARIO

    @property
    def es_interbibliotecario(self):
        return self.tipo == TipoPrestamo.INTERBIBLIOTECARIO

    @property
    def esta_abierto(self):
        """True mientras el préstamo ocupa el ejemplar."""
        return self._estado in (P.PENDIENTE_ENVIO, P.LISTO_PARA_RETIRO,
                                P.ACTIVO)

    def _exigir_estado(self, *permitidos):
        if self._estado not in permitidos:
            raise TransicionInvalidaError(
                f"Operación no permitida: el préstamo #{self.id} está en "
                f"estado {self._estado.value}")

    def marcar_listo_para_retiro(self):
        self._exigir_estado(P.PENDIENTE_ENVIO)
        self._estado = P.LISTO_PARA_RETIRO

    def activar(self, fecha):
        """Entrega el ejemplar al socio y fija el vencimiento."""
        self._exigir_estado(P.LISTO_PARA_RETIRO)
        self._estado = P.ACTIVO
        self.fecha_inicio = fecha
        self.fecha_vencimiento = fecha + timedelta(days=self.dias_prestamo)

    def cancelar(self, motivo):
        self._exigir_estado(P.PENDIENTE_ENVIO, P.LISTO_PARA_RETIRO)
        self._estado = P.CANCELADO
        self.observaciones = motivo

    def dias_atraso(self, hoy):
        """Días de atraso a la fecha indicada (o a la fecha de devolución)."""
        if self.fecha_vencimiento is None:
            return 0
        referencia = self.fecha_devolucion or hoy
        return max((referencia - self.fecha_vencimiento).days, 0)

    def esta_vencido(self, hoy):
        return self._estado == P.ACTIVO and self.dias_atraso(hoy) > 0

    def multa_estimada(self, hoy):
        """Multa acumulada hasta hoy si se devolviera en buen estado."""
        if self._estado != P.ACTIVO:
            return self.multa
        return self.politica_multa.calcular_total(self.dias_atraso(hoy))

    def registrar_devolucion(self, fecha, condicion, observaciones=""):
        """
        Cierra el préstamo calculando la multa por atraso y por estado físico.

        :return: multa aplicada
        :rtype: float
        """
        self._exigir_estado(P.ACTIVO)
        self.fecha_devolucion = fecha
        self.condicion_devolucion = CondicionFisica(condicion)
        self.multa = self.politica_multa.calcular_total(
            self.dias_atraso(fecha), self.condicion_devolucion)
        self.observaciones = observaciones
        self._estado = P.DEVUELTO
        return self.multa
