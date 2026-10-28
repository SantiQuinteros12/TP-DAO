"""
Abstracción del tiempo.

Inyectar el reloj en los servicios permite testear reglas dependientes de
fechas (vencimientos, multas, tiempos de tránsito) y generar datos de
prueba históricos sin modificar la lógica de negocio.
"""

from abc import ABC, abstractmethod
from datetime import datetime, timedelta


class Reloj(ABC):

    @abstractmethod
    def ahora(self):
        """
        :return: fecha y hora actual
        :rtype: datetime
        """

    def hoy(self):
        return self.ahora().date()


class RelojSistema(Reloj):

    def ahora(self):
        return datetime.now().replace(microsecond=0)


class RelojFijo(Reloj):
    """Reloj controlable manualmente (tests y datos de ejemplo)."""

    def __init__(self, instante):
        self._instante = instante

    def ahora(self):
        return self._instante

    def avanzar(self, dias=0, horas=0):
        self._instante += timedelta(days=dias, hours=horas)

    def fijar(self, instante):
        self._instante = instante
