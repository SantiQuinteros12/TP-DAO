"""
Patrón STRATEGY: políticas de cálculo de multas.

Cada tipo de préstamo usa una política distinta; el Prestamo delega el
cálculo sin conocer la fórmula (Open/Closed: agregar una política nueva no
requiere modificar Prestamo).
"""

from abc import ABC, abstractmethod

from domain.enums import CondicionFisica, TipoPrestamo

RECARGO_DETERIORO = 2000.0
RECARGO_DANO = 15000.0


class PoliticaMulta(ABC):

    nombre = "abstracta"

    @abstractmethod
    def calcular_por_atraso(self, dias_atraso):
        """
        :param dias_atraso: días transcurridos desde el vencimiento
        :type dias_atraso: int
        :rtype: float
        """

    def recargo_por_condicion(self, condicion):
        """Recargo por el estado físico en que se devuelve el material."""
        return {
            CondicionFisica.BUENA: 0.0,
            CondicionFisica.DETERIORADA: RECARGO_DETERIORO,
            CondicionFisica.DANADA: RECARGO_DANO,
        }[CondicionFisica(condicion)]

    def calcular_total(self, dias_atraso, condicion=CondicionFisica.BUENA):
        return round(self.calcular_por_atraso(max(dias_atraso, 0))
                     + self.recargo_por_condicion(condicion), 2)


class MultaLineal(PoliticaMulta):
    """Monto fijo por cada día de atraso (préstamos locales)."""

    nombre = "lineal"

    def __init__(self, monto_diario=500.0):
        self.monto_diario = monto_diario

    def calcular_por_atraso(self, dias_atraso):
        return dias_atraso * self.monto_diario


class MultaEscalonada(PoliticaMulta):
    """
    Préstamos interbibliotecarios: el atraso retiene material de otra sede,
    por lo que a partir de cierto umbral el monto diario se multiplica.
    """

    nombre = "escalonada"

    def __init__(self, monto_diario=500.0, umbral_dias=7, factor=2.0):
        self.monto_diario = monto_diario
        self.umbral_dias = umbral_dias
        self.factor = factor

    def calcular_por_atraso(self, dias_atraso):
        normales = min(dias_atraso, self.umbral_dias)
        agravados = max(dias_atraso - self.umbral_dias, 0)
        return (normales * self.monto_diario
                + agravados * self.monto_diario * self.factor)


def politica_para(tipo):
    """
    Devuelve la política de multa correspondiente a un tipo de préstamo.

    :type tipo: TipoPrestamo
    :rtype: PoliticaMulta
    """
    if TipoPrestamo(tipo) == TipoPrestamo.INTERBIBLIOTECARIO:
        return MultaEscalonada()
    return MultaLineal()
