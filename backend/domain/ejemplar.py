"""
Entidad EjemplarFisico.

El ciclo de vida del ejemplar es acotado y sus estados no cambian el
comportamiento del objeto, sólo restringen transiciones; por eso se modela
con una tabla de transiciones (a diferencia del Remito, que usa State).
"""

from domain.enums import CondicionFisica, EstadoEjemplar
from domain.excepciones import DatoInvalidoError, TransicionInvalidaError

E = EstadoEjemplar

_TRANSICIONES = {
    E.DISPONIBLE: {E.RESERVADO, E.EN_PRESTAMO, E.EN_TRANSITO, E.DANADO, E.BAJA},
    E.RESERVADO: {E.DISPONIBLE, E.EN_PRESTAMO, E.EN_TRANSITO, E.BAJA},
    E.EN_PRESTAMO: {E.DISPONIBLE, E.RESERVADO, E.DANADO},
    E.EN_TRANSITO: {E.DISPONIBLE, E.RESERVADO, E.DANADO, E.BAJA},
    E.DANADO: {E.DISPONIBLE, E.EN_TRANSITO, E.BAJA},
    E.BAJA: set(),
}


class Ejemplar:
    """
    Copia física de un libro.

    :param isbn: libro al que corresponde
    :param sede_id: sede propietaria (a la que pertenece el ejemplar)
    :param sede_actual_id: sede donde se encuentra físicamente
    :param codigo_inventario: código único de inventario (ej. "CEN-0001")
    """

    def __init__(self, isbn, sede_id, codigo_inventario,
                 estado=EstadoEjemplar.DISPONIBLE,
                 condicion=CondicionFisica.BUENA, sede_actual_id=None,
                 id=None):
        self.id = id
        self.isbn = isbn
        self.sede_id = sede_id
        self.sede_actual_id = sede_actual_id if sede_actual_id else sede_id
        self.codigo_inventario = (codigo_inventario or "").strip().upper()
        self._estado = EstadoEjemplar(estado)
        self.condicion = CondicionFisica(condicion)
        if not self.codigo_inventario:
            raise DatoInvalidoError("El código de inventario es obligatorio")

    @property
    def estado(self):
        return self._estado

    @property
    def esta_disponible(self):
        return self._estado == E.DISPONIBLE

    @property
    def esta_en_su_sede(self):
        return self.sede_actual_id == self.sede_id

    def _cambiar_estado(self, nuevo):
        if nuevo not in _TRANSICIONES[self._estado]:
            raise TransicionInvalidaError(
                f"El ejemplar {self.codigo_inventario} no puede pasar de "
                f"{self._estado.value} a {nuevo.value}")
        self._estado = nuevo

    def reservar(self):
        """Retiene el ejemplar para un préstamo, reserva o envío."""
        self._cambiar_estado(E.RESERVADO)

    def liberar(self):
        """Vuelve a dejarlo disponible (ej. reserva cancelada)."""
        self._cambiar_estado(E.DISPONIBLE)

    def prestar(self):
        self._cambiar_estado(E.EN_PRESTAMO)

    def despachar(self):
        self._cambiar_estado(E.EN_TRANSITO)

    def recibir_en(self, sede_id, condicion, quedar_reservado):
        """
        Registra la llegada física del ejemplar a una sede.

        :param quedar_reservado: True si llega para un préstamo pendiente
        """
        self.sede_actual_id = sede_id
        self.condicion = CondicionFisica(condicion)
        if self.condicion == CondicionFisica.DANADA:
            self._cambiar_estado(E.DANADO)
        elif quedar_reservado:
            self._cambiar_estado(E.RESERVADO)
        else:
            self._cambiar_estado(E.DISPONIBLE)

    def registrar_devolucion(self, condicion, queda_retenido):
        """
        :param queda_retenido: True si debe retornar a su sede propietaria
                               (queda reservado para el remito de retorno)
        """
        self.condicion = CondicionFisica(condicion)
        if self.condicion == CondicionFisica.DANADA and not queda_retenido:
            self._cambiar_estado(E.DANADO)
        elif queda_retenido:
            self._cambiar_estado(E.RESERVADO)
        else:
            self._cambiar_estado(E.DISPONIBLE)

    def reparar(self):
        self.condicion = CondicionFisica.DETERIORADA
        self._cambiar_estado(E.DISPONIBLE)

    def dar_de_baja(self):
        self._cambiar_estado(E.BAJA)

    def transferir_propiedad(self, sede_id):
        """Cambia la sede propietaria (al recibir un TRASLADO)."""
        self.sede_id = sede_id
