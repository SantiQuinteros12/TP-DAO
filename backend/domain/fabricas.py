"""
Patrón FACTORY METHOD: creación de préstamos.

``CreadorPrestamo.crear`` define el algoritmo común (validaciones de negocio
compartidas) y delega en las subclases el método fábrica
``_construir_prestamo`` y las reglas propias de cada tipo. El servicio pide
el creador adecuado a ``creador_para`` y nunca instancia Prestamo
directamente.
"""

from abc import ABC, abstractmethod

from domain.enums import EstadoEjemplar, EstadoPrestamo
from domain.excepciones import ReglaNegocioError
from domain.multas import MultaEscalonada, MultaLineal
from domain.prestamo import Prestamo


class CreadorPrestamo(ABC):

    dias_prestamo = 14

    def crear(self, socio, ejemplar, sede_origen, sede_destino, hoy,
              reserva_id=None):
        """
        Valida las reglas de negocio y crea el préstamo, ocupando el ejemplar.

        :param reserva_id: si el ejemplar está RESERVADO para este socio por
                           una reserva, permite prestarlo
        :rtype: Prestamo
        """
        self._validar_comunes(socio, ejemplar, sede_origen, sede_destino,
                              reserva_id)
        self._validar_especificas(sede_origen, sede_destino)
        prestamo = self._construir_prestamo(socio, ejemplar, sede_origen,
                                            sede_destino, hoy)
        prestamo.reserva_id = reserva_id
        self._ocupar_ejemplar(ejemplar, prestamo, hoy)
        return prestamo

    @staticmethod
    def _validar_comunes(socio, ejemplar, sede_origen, sede_destino,
                         reserva_id):
        socio.verificar_puede_operar()
        sede_origen.verificar_operativa()
        sede_destino.verificar_operativa()
        if ejemplar.sede_id != sede_origen.id:
            raise ReglaNegocioError(
                f"El ejemplar {ejemplar.codigo_inventario} no pertenece a la "
                f"sede de origen '{sede_origen.nombre}'")
        if ejemplar.sede_actual_id != sede_origen.id:
            raise ReglaNegocioError(
                f"El ejemplar {ejemplar.codigo_inventario} no se encuentra "
                f"físicamente en la sede '{sede_origen.nombre}'")
        reservado_ok = (reserva_id is not None
                        and ejemplar.estado == EstadoEjemplar.RESERVADO)
        if not ejemplar.esta_disponible and not reservado_ok:
            raise ReglaNegocioError(
                f"El ejemplar {ejemplar.codigo_inventario} no está disponible "
                f"(estado: {ejemplar.estado.value})")

    def _validar_especificas(self, sede_origen, sede_destino):
        """Gancho para reglas propias de cada tipo de préstamo."""

    @abstractmethod
    def _construir_prestamo(self, socio, ejemplar, sede_origen, sede_destino,
                            hoy):
        """Método fábrica."""

    @abstractmethod
    def _ocupar_ejemplar(self, ejemplar, prestamo, hoy):
        """Cambia el estado del ejemplar según el tipo de préstamo."""


class CreadorPrestamoLocal(CreadorPrestamo):
    """El socio retira el ejemplar en la misma sede: queda ACTIVO al crearse."""

    dias_prestamo = 14

    def _validar_especificas(self, sede_origen, sede_destino):
        if sede_origen.id != sede_destino.id:
            raise ReglaNegocioError(
                "Un préstamo local requiere misma sede de origen y destino")

    def _construir_prestamo(self, socio, ejemplar, sede_origen, sede_destino,
                            hoy):
        return Prestamo(
            socio_id=socio.id, ejemplar_id=ejemplar.id,
            sede_origen_id=sede_origen.id, sede_destino_id=sede_destino.id,
            fecha_solicitud=hoy, dias_prestamo=self.dias_prestamo,
            estado=EstadoPrestamo.LISTO_PARA_RETIRO,
            politica_multa=MultaLineal())

    def _ocupar_ejemplar(self, ejemplar, prestamo, hoy):
        ejemplar.prestar()
        prestamo.activar(hoy)


class CreadorPrestamoInterbibliotecario(CreadorPrestamo):
    """
    El ejemplar viaja de la sede origen a la sede destino mediante un remito;
    el plazo empieza a correr recién cuando el socio lo retira.
    """

    dias_prestamo = 21

    def _validar_especificas(self, sede_origen, sede_destino):
        if sede_origen.id == sede_destino.id:
            raise ReglaNegocioError(
                "Un préstamo interbibliotecario requiere sedes distintas")

    def _construir_prestamo(self, socio, ejemplar, sede_origen, sede_destino,
                            hoy):
        return Prestamo(
            socio_id=socio.id, ejemplar_id=ejemplar.id,
            sede_origen_id=sede_origen.id, sede_destino_id=sede_destino.id,
            fecha_solicitud=hoy, dias_prestamo=self.dias_prestamo,
            estado=EstadoPrestamo.PENDIENTE_ENVIO,
            politica_multa=MultaEscalonada())

    def _ocupar_ejemplar(self, ejemplar, prestamo, hoy):
        if ejemplar.esta_disponible:
            ejemplar.reservar()


def creador_para(sede_origen_id, sede_destino_id):
    """
    Selecciona el creador concreto según las sedes involucradas.

    :rtype: CreadorPrestamo
    """
    if sede_origen_id == sede_destino_id:
        return CreadorPrestamoLocal()
    return CreadorPrestamoInterbibliotecario()
