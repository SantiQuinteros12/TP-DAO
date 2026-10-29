"""Enumeraciones del dominio (valores persistidos como texto)."""

from enum import Enum


class EstadoEjemplar(str, Enum):
    DISPONIBLE = "DISPONIBLE"
    RESERVADO = "RESERVADO"
    EN_PRESTAMO = "EN_PRESTAMO"
    EN_TRANSITO = "EN_TRANSITO"
    DANADO = "DANADO"
    BAJA = "BAJA"


class CondicionFisica(str, Enum):
    """Estado físico del material, evaluado en devoluciones y recepciones."""

    BUENA = "BUENA"
    DETERIORADA = "DETERIORADA"
    DANADA = "DANADA"

    @property
    def gravedad(self):
        return list(CondicionFisica).index(self)

    def peor(self, otra):
        """La más grave entre ambas (``otra`` puede ser None)."""
        if otra is None:
            return self
        otra = CondicionFisica(otra)
        return otra if otra.gravedad > self.gravedad else self


class TipoPrestamo(str, Enum):
    LOCAL = "LOCAL"
    INTERBIBLIOTECARIO = "INTERBIBLIOTECARIO"


class EstadoPrestamo(str, Enum):
    PENDIENTE_ENVIO = "PENDIENTE_ENVIO"
    LISTO_PARA_RETIRO = "LISTO_PARA_RETIRO"
    ACTIVO = "ACTIVO"
    DEVUELTO = "DEVUELTO"
    CANCELADO = "CANCELADO"


class EstadoReserva(str, Enum):
    PENDIENTE = "PENDIENTE"
    DISPONIBLE = "DISPONIBLE"
    CUMPLIDA = "CUMPLIDA"
    CANCELADA = "CANCELADA"
    VENCIDA = "VENCIDA"


class TipoRemito(str, Enum):
    ENVIO = "ENVIO"          # sede origen -> sede destino de un préstamo
    RETORNO = "RETORNO"      # vuelta del ejemplar a su sede propietaria
    TRASLADO = "TRASLADO"    # reasignación permanente del ejemplar


class TipoIncidencia(str, Enum):
    DEMORA = "DEMORA"
    DANO = "DANO"
    EXTRAVIO = "EXTRAVIO"
    OTRO = "OTRO"
