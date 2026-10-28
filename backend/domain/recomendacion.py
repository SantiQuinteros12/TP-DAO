"""
Motor de recomendaciones de lectura.

Cada criterio es una Strategy que puntúa un libro candidato entre 0 y 1 y
puede aportar un motivo legible. El motor (Composite) combina los criterios
con pesos, de modo que agregar un criterio nuevo no modifica el motor
(principio abierto/cerrado).
"""

from abc import ABC, abstractmethod
from collections import Counter
from dataclasses import dataclass, field


@dataclass
class ContextoRecomendacion:
    """
    Datos de lectura sobre los que se recomienda.

    :param libros: isbn -> dict con titulo, autor, genero, disponibles,
        prestamos_recientes, etc.
    :param lectores: isbn -> conjunto de socios que lo pidieron prestado
    :param leidos: ISBN que el lector ya conoce (no se recomiendan)
    :param socio_id: lector al que se recomienda (se excluye de los afines)
    """
    libros: dict
    lectores: dict
    leidos: set = field(default_factory=set)
    socio_id: int = None

    def __post_init__(self):
        leidos = [self.libros[i] for i in self.leidos if i in self.libros]
        self.generos = Counter(l["genero"] for l in leidos if l["genero"])
        self.autores = Counter(l["autor"] for l in leidos)
        # Socios que leyeron algo en común con el lector.
        self.afines = set().union(*(self.lectores.get(i, set())
                                    for i in self.leidos)) if leidos else set()
        self.afines.discard(self.socio_id)
        self.max_recientes = max(
            (l["prestamos_recientes"] for l in self.libros.values()),
            default=0) or 1

    @property
    def tiene_historial(self):
        return bool(self.generos or self.autores)


class CriterioRecomendacion(ABC):
    """Strategy: puntúa un candidato. ``peso`` define su importancia."""

    peso = 1.0

    @abstractmethod
    def puntuar(self, libro, ctx):
        """:return: (puntaje entre 0 y 1, motivo o None)"""


class CriterioGenero(CriterioRecomendacion):
    peso = 3.0

    def puntuar(self, libro, ctx):
        total = sum(ctx.generos.values())
        veces = ctx.generos.get(libro["genero"], 0)
        if not veces:
            return 0.0, None
        return veces / total, f"Te interesa el género {libro['genero']}"


class CriterioAutor(CriterioRecomendacion):
    peso = 2.5

    def puntuar(self, libro, ctx):
        if libro["autor"] in ctx.autores:
            return 1.0, f"Leíste otras obras de {libro['autor']}"
        return 0.0, None


class CriterioColaborativo(CriterioRecomendacion):
    """"Lectores con gustos parecidos también leyeron…"."""

    peso = 2.0

    def puntuar(self, libro, ctx):
        if not ctx.afines:
            return 0.0, None
        coinciden = len(ctx.lectores.get(libro["isbn"], set()) & ctx.afines)
        if not coinciden:
            return 0.0, None
        return (coinciden / len(ctx.afines),
                f"Lo leyeron {coinciden} socio(s) con gustos parecidos")


class CriterioPopularidad(CriterioRecomendacion):
    peso = 1.0

    def puntuar(self, libro, ctx):
        puntaje = libro["prestamos_recientes"] / ctx.max_recientes
        motivo = "Muy pedido en la red últimamente" if puntaje >= 0.6 else None
        return puntaje, motivo


class CriterioDisponibilidad(CriterioRecomendacion):
    peso = 0.8

    def puntuar(self, libro, ctx):
        if libro["disponibles"]:
            return 1.0, "Disponible ahora para retirar"
        return 0.0, None


@dataclass
class Recomendacion:
    libro: dict
    puntaje: float
    motivos: list


class MotorRecomendacion:
    """
    Combina criterios ponderados. El puntaje final se normaliza a 0-100
    respecto del máximo alcanzable con los criterios configurados.
    """

    def __init__(self, criterios):
        self.criterios = list(criterios)
        self._maximo = sum(c.peso for c in self.criterios) or 1

    @classmethod
    def personalizado(cls):
        return cls([CriterioGenero(), CriterioAutor(), CriterioColaborativo(),
                    CriterioPopularidad(), CriterioDisponibilidad()])

    @classmethod
    def por_tendencia(cls):
        """Sin historial (arranque en frío): popularidad y disponibilidad."""
        return cls([CriterioPopularidad(), CriterioDisponibilidad()])

    def recomendar(self, ctx, limite=8):
        resultado = []
        for isbn, libro in ctx.libros.items():
            if isbn in ctx.leidos:
                continue
            total, motivos = 0.0, []
            for criterio in self.criterios:
                puntaje, motivo = criterio.puntuar(libro, ctx)
                total += criterio.peso * puntaje
                if motivo:
                    motivos.append(motivo)
            if total > 0:
                resultado.append(Recomendacion(
                    libro, round(100 * total / self._maximo), motivos))
        resultado.sort(key=lambda r: (-r.puntaje, r.libro["titulo"]))
        return resultado[:limite]
