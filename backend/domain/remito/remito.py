"""Entidad Remito: documento que acompaña un ejemplar entre sedes."""

from dataclasses import dataclass

from domain.enums import CondicionFisica, TipoIncidencia, TipoRemito
from domain.eventos import RegistroEventos, RemitoCambioEstado
from domain.excepciones import DatoInvalidoError, ReglaNegocioError
from domain.remito.estados import Creado, EstadoRemito, estado_desde_nombre


@dataclass(frozen=True)
class MovimientoRemito:
    """
    Value Object: entrada inmutable del historial de trazabilidad.
    Cada transición del remito agrega exactamente un movimiento.
    """

    estado: str
    fecha_hora: object
    responsable: str = ""
    ubicacion: str = ""
    observacion: str = ""
    tipo_incidencia: str = None
    condicion: str = None


@dataclass
class ContextoTransicion:
    """Datos que acompañan a una operación sobre el remito."""

    fecha_hora: object
    responsable: str = ""
    ubicacion: str = ""
    observacion: str = ""
    tipo_incidencia: TipoIncidencia = None
    condicion: CondicionFisica = None


class Remito(RegistroEventos):
    """
    Contexto del patrón State: delega cada operación en su estado actual.

    :param tipo: ENVIO, RETORNO o TRASLADO
    :param prestamo_id: préstamo asociado (None para TRASLADO)
    """

    def __init__(self, ejemplar_id, sede_origen_id, sede_destino_id, tipo,
                 fecha_creacion, prestamo_id=None, estado=None,
                 historial=None, id=None):
        super().__init__()
        if sede_origen_id == sede_destino_id:
            raise DatoInvalidoError(
                "Sede origen y destino del remito deben ser distintas")
        self.id = id
        self.ejemplar_id = ejemplar_id
        self.sede_origen_id = sede_origen_id
        self.sede_destino_id = sede_destino_id
        self.tipo = TipoRemito(tipo)
        self.prestamo_id = prestamo_id
        self.fecha_creacion = fecha_creacion
        self._historial = list(historial or [])
        if estado is None:
            self._estado = Creado()
            self._historial.append(MovimientoRemito(
                Creado.nombre, fecha_creacion,
                observacion=f"Remito de {self.tipo.value.lower()} generado"))
        else:
            self._estado = (estado if isinstance(estado, EstadoRemito)
                            else estado_desde_nombre(estado))

    # --- consultas -------------------------------------------------------
    @property
    def numero(self):
        return f"R-{self.id:06d}" if self.id else "R-(nuevo)"

    @property
    def estado(self):
        return self._estado.nombre

    @property
    def finalizado(self):
        return self._estado.es_final

    @property
    def historial(self):
        return tuple(self._historial)

    @property
    def acciones_disponibles(self):
        return self._estado.acciones_disponibles()

    @property
    def tuvo_incidencias(self):
        return any(m.tipo_incidencia for m in self._historial)

    def fecha_de(self, estado):
        """Primera fecha en que el remito alcanzó ``estado`` (o None)."""
        return next((m.fecha_hora for m in self._historial
                     if m.estado == estado), None)

    @property
    def condicion_recepcion(self):
        recibido = [m for m in self._historial if m.estado == "RECIBIDO"]
        return recibido[-1].condicion if recibido else None

    # --- operaciones (delegadas al estado) -------------------------------
    def empaquetar(self, ctx):
        self._estado.empaquetar(self, ctx)

    def despachar(self, ctx):
        self._estado.despachar(self, ctx)

    def registrar_checkpoint(self, ctx):
        if not ctx.ubicacion:
            raise DatoInvalidoError("El checkpoint requiere una ubicación")
        self._estado.registrar_checkpoint(self, ctx)

    def recibir(self, ctx):
        ctx.condicion = CondicionFisica(ctx.condicion or CondicionFisica.BUENA)
        self._estado.recibir(self, ctx)

    def reportar_incidencia(self, ctx):
        if not ctx.tipo_incidencia:
            raise DatoInvalidoError("Debe indicar el tipo de incidencia")
        if not ctx.observacion:
            raise DatoInvalidoError("Debe describir la incidencia")
        ctx.tipo_incidencia = TipoIncidencia(ctx.tipo_incidencia)
        self._estado.reportar_incidencia(self, ctx)

    def resolver_incidencia(self, ctx):
        self._estado.resolver_incidencia(self, ctx)

    def declarar_extravio(self, ctx):
        self._estado.declarar_extravio(self, ctx)

    def cancelar(self, ctx):
        if not ctx.observacion:
            raise DatoInvalidoError("Debe indicar el motivo de la cancelación")
        self._estado.cancelar(self, ctx)

    # --- usado sólo por los estados --------------------------------------
    def _transicionar(self, nuevo_estado, ctx):
        ultimo = self._historial[-1].fecha_hora if self._historial else None
        if ultimo and ctx.fecha_hora < ultimo:
            raise ReglaNegocioError(
                "La fecha del movimiento no puede ser anterior al último "
                "registrado en el remito")
        anterior = self._estado.nombre
        self._estado = nuevo_estado
        self._historial.append(MovimientoRemito(
            estado=nuevo_estado.nombre,
            fecha_hora=ctx.fecha_hora,
            responsable=ctx.responsable or "",
            ubicacion=ctx.ubicacion or "",
            observacion=ctx.observacion or "",
            tipo_incidencia=(ctx.tipo_incidencia.value
                             if ctx.tipo_incidencia else None),
            condicion=ctx.condicion.value if ctx.condicion else None,
        ))
        self.registrar_evento(RemitoCambioEstado(
            ocurrido_en=ctx.fecha_hora, remito_id=self.id,
            tipo_remito=self.tipo.value, prestamo_id=self.prestamo_id,
            estado_anterior=anterior, estado_nuevo=nuevo_estado.nombre,
            observacion=ctx.observacion or ""))
