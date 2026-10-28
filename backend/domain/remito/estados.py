"""
Patrón STATE: estados del ciclo de vida del Remito.

Diagrama de estados:

    CREADO ──empaquetar──> EMPAQUETADO ──despachar──> DESPACHADO
      │                        │                         │
      cancelar                 cancelar                  checkpoint
      ▼                        ▼                         ▼
    CANCELADO               (...)                    EN_TRANSITO ──┐ checkpoint
                                                     │     │  ◄────┘
                                                recibir  incidencia
                                                     ▼     ▼
                                                RECIBIDO  CON_INCIDENCIA
                                                     ▲     │  │
                                                     └─────┘  │ resolver -> EN_TRANSITO
                                               recibir        └ declarar_extravio -> EXTRAVIADO

Cada clase concreta implementa sólo las operaciones válidas en ese estado;
el resto hereda la implementación por defecto que lanza
TransicionInvalidaError. Así, agregar un estado nuevo no obliga a modificar
los existentes ni a mantener condicionales dispersos en el Remito.
"""

from abc import ABC

from domain.excepciones import TransicionInvalidaError


class EstadoRemito(ABC):
    """Estado abstracto. ``nombre`` es el valor persistido."""

    nombre = None
    es_final = False

    def _invalida(self, remito, accion):
        raise TransicionInvalidaError(
            f"No se puede '{accion}' el remito {remito.numero}: "
            f"está en estado {self.nombre}")

    # --- operaciones (por defecto inválidas) -----------------------------
    def empaquetar(self, remito, ctx):
        self._invalida(remito, "empaquetar")

    def despachar(self, remito, ctx):
        self._invalida(remito, "despachar")

    def registrar_checkpoint(self, remito, ctx):
        self._invalida(remito, "registrar checkpoint en")

    def recibir(self, remito, ctx):
        self._invalida(remito, "recibir")

    def reportar_incidencia(self, remito, ctx):
        self._invalida(remito, "reportar incidencia en")

    def resolver_incidencia(self, remito, ctx):
        self._invalida(remito, "resolver incidencia de")

    def declarar_extravio(self, remito, ctx):
        self._invalida(remito, "declarar extraviado")

    def cancelar(self, remito, ctx):
        self._invalida(remito, "cancelar")

    @classmethod
    def acciones_disponibles(cls):
        """Operaciones que este estado redefine (las únicas válidas)."""
        return [nombre for nombre in ACCIONES
                if getattr(cls, nombre) is not getattr(EstadoRemito, nombre)]

    def __eq__(self, otro):
        return isinstance(otro, EstadoRemito) and otro.nombre == self.nombre

    def __hash__(self):
        return hash(self.nombre)

    def __repr__(self):
        return f"<EstadoRemito {self.nombre}>"


ACCIONES = ("empaquetar", "despachar", "registrar_checkpoint", "recibir",
            "reportar_incidencia", "resolver_incidencia", "declarar_extravio",
            "cancelar")


class Creado(EstadoRemito):
    nombre = "CREADO"

    def empaquetar(self, remito, ctx):
        remito._transicionar(Empaquetado(), ctx)

    def cancelar(self, remito, ctx):
        remito._transicionar(Cancelado(), ctx)


class Empaquetado(EstadoRemito):
    nombre = "EMPAQUETADO"

    def despachar(self, remito, ctx):
        remito._transicionar(Despachado(), ctx)

    def cancelar(self, remito, ctx):
        remito._transicionar(Cancelado(), ctx)


class Despachado(EstadoRemito):
    nombre = "DESPACHADO"

    def registrar_checkpoint(self, remito, ctx):
        remito._transicionar(EnTransito(), ctx)

    def recibir(self, remito, ctx):
        remito._transicionar(Recibido(), ctx)

    def reportar_incidencia(self, remito, ctx):
        remito._transicionar(ConIncidencia(), ctx)


class EnTransito(EstadoRemito):
    nombre = "EN_TRANSITO"

    def registrar_checkpoint(self, remito, ctx):
        # Permanece en tránsito pero deja constancia del punto de control.
        remito._transicionar(EnTransito(), ctx)

    def recibir(self, remito, ctx):
        remito._transicionar(Recibido(), ctx)

    def reportar_incidencia(self, remito, ctx):
        remito._transicionar(ConIncidencia(), ctx)


class ConIncidencia(EstadoRemito):
    nombre = "CON_INCIDENCIA"

    def resolver_incidencia(self, remito, ctx):
        remito._transicionar(EnTransito(), ctx)

    def recibir(self, remito, ctx):
        remito._transicionar(Recibido(), ctx)

    def declarar_extravio(self, remito, ctx):
        remito._transicionar(Extraviado(), ctx)


class Recibido(EstadoRemito):
    nombre = "RECIBIDO"
    es_final = True


class Extraviado(EstadoRemito):
    nombre = "EXTRAVIADO"
    es_final = True


class Cancelado(EstadoRemito):
    nombre = "CANCELADO"
    es_final = True


_ESTADOS = {cls.nombre: cls for cls in (Creado, Empaquetado, Despachado,
                                        EnTransito, ConIncidencia, Recibido,
                                        Extraviado, Cancelado)}

NOMBRES_ESTADOS = tuple(_ESTADOS)
ESTADOS_EN_CURSO = tuple(n for n, c in _ESTADOS.items() if not c.es_final)


def estado_desde_nombre(nombre):
    """Reconstruye el objeto estado a partir del valor persistido."""
    try:
        return _ESTADOS[nombre]()
    except KeyError:
        raise ValueError(f"Estado de remito desconocido: {nombre}")
