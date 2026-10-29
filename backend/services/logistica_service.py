"""
Caso de uso: empaquetar, despachar, seguir y recibir ejemplares (remitos).

El Remito (patrón State) decide si una operación es válida; este servicio
aplica las consecuencias sobre el ejemplar y el préstamo asociados según el
tipo de remito y el estado alcanzado.
"""

from domain.enums import CondicionFisica, EstadoEjemplar, TipoRemito
from domain.excepciones import DatoInvalidoError, ReglaNegocioError
from domain.remito import ContextoTransicion, Remito
from services.base import ServicioBase
from services.reserva_service import ReservaService

OPERACIONES = ("empaquetar", "despachar", "registrar_checkpoint", "recibir",
               "reportar_incidencia", "resolver_incidencia",
               "declarar_extravio", "cancelar")


class LogisticaService(ServicioBase):

    def __init__(self, uow, reloj, publicador=None):
        super().__init__(uow, reloj, publicador)
        self._reservas = ReservaService(uow, reloj, self.publicador)

    def obtener(self, remito_id):
        return self._requerir(self.uow.remitos, remito_id, "Remito")

    # --- creación --------------------------------------------------------
    def crear_remito(self, tipo, ejemplar, sede_origen_id, sede_destino_id,
                     prestamo_id=None):
        """
        Genera el remito que acompañará al ejemplar.

        :raises ReglaNegocioError: si alguna sede está dada de baja o el
                                   ejemplar ya tiene un remito en curso
        """
        for sede_id in (sede_origen_id, sede_destino_id):
            self._requerir(self.uow.sedes, sede_id,
                           "Sede").verificar_operativa()
        en_curso = self.uow.remitos.en_curso_de_ejemplar(ejemplar.id)
        if en_curso:
            raise ReglaNegocioError(
                f"El ejemplar {ejemplar.codigo_inventario} ya viaja con el "
                f"remito {en_curso.numero}")
        remito = Remito(ejemplar.id, sede_origen_id, sede_destino_id, tipo,
                        self.reloj.ahora(), prestamo_id)
        return self.uow.remitos.guardar(remito)

    def trasladar_ejemplar(self, ejemplar_id, sede_destino_id):
        """Reasigna un ejemplar a otra sede mediante un remito de TRASLADO."""
        ejemplar = self._requerir(self.uow.ejemplares, ejemplar_id,
                                  "Ejemplar")
        if not (ejemplar.esta_disponible and ejemplar.esta_en_su_sede):
            raise ReglaNegocioError(
                "Sólo se pueden trasladar ejemplares disponibles en su sede")
        if ejemplar.sede_id == sede_destino_id:
            raise ReglaNegocioError("El ejemplar ya pertenece a esa sede")
        remito = self.crear_remito(TipoRemito.TRASLADO, ejemplar,
                                   ejemplar.sede_id, sede_destino_id)
        ejemplar.reservar()
        self.uow.ejemplares.guardar(ejemplar)
        return remito

    # --- operaciones sobre el ciclo de vida ------------------------------
    def operar(self, remito_id, operacion, responsable="", ubicacion="",
               observacion="", tipo_incidencia=None, condicion=None):
        """
        Ejecuta una operación del ciclo de vida del remito y propaga sus
        efectos. Las operaciones válidas dependen del estado actual
        (ver ``Remito.acciones_disponibles``).
        """
        if operacion not in OPERACIONES:
            raise DatoInvalidoError(f"Operación desconocida: {operacion}")
        remito = self.obtener(remito_id)
        if operacion == "despachar":
            for sede_id in (remito.sede_origen_id, remito.sede_destino_id):
                self.uow.sedes.obtener(sede_id).verificar_operativa()
        if operacion == "cancelar" and remito.tipo == TipoRemito.RETORNO:
            raise ReglaNegocioError(
                "Un remito de retorno no puede cancelarse: el ejemplar debe "
                "volver a su sede propietaria")
        ctx = ContextoTransicion(
            fecha_hora=self.reloj.ahora(), responsable=responsable,
            ubicacion=ubicacion, observacion=observacion,
            tipo_incidencia=tipo_incidencia,
            condicion=CondicionFisica(condicion) if condicion else None)
        if operacion == "recibir":
            # El viaje no mejora el material: se registra la peor condición
            # entre la que traía el ejemplar y la informada (si hay).
            ejemplar = self.uow.ejemplares.obtener(remito.ejemplar_id)
            ctx.condicion = ejemplar.condicion.peor(ctx.condicion)
        getattr(remito, operacion)(ctx)
        self.uow.remitos.guardar(remito)
        self._aplicar_efectos(remito, ctx)
        self._publicar_de(remito)
        return remito

    def _aplicar_efectos(self, remito, ctx):
        ejemplar = self.uow.ejemplares.obtener(remito.ejemplar_id)
        prestamo = (self.uow.prestamos.obtener(remito.prestamo_id)
                    if remito.prestamo_id else None)
        manejador = {
            "DESPACHADO": self._al_despachar,
            "RECIBIDO": self._al_recibir,
            "EXTRAVIADO": self._al_extraviarse,
            "CANCELADO": self._al_cancelar,
        }.get(remito.estado)
        if manejador:
            manejador(remito, ejemplar, prestamo, ctx)
        self.uow.ejemplares.guardar(ejemplar)
        if prestamo:
            self.uow.prestamos.guardar(prestamo)

    def _al_despachar(self, remito, ejemplar, prestamo, ctx):
        ejemplar.despachar()

    def _al_recibir(self, remito, ejemplar, prestamo, ctx):
        if remito.tipo == TipoRemito.TRASLADO:
            ejemplar.transferir_propiedad(remito.sede_destino_id)
        llega_para_prestamo = remito.tipo == TipoRemito.ENVIO
        ejemplar.recibir_en(remito.sede_destino_id, ctx.condicion,
                            quedar_reservado=llega_para_prestamo)
        if llega_para_prestamo:
            if ejemplar.estado == EstadoEjemplar.DANADO:
                prestamo.cancelar("Ejemplar recibido dañado en sede destino")
                self.uow.prestamos.guardar(prestamo)
                self.crear_remito(TipoRemito.RETORNO, ejemplar,
                                  remito.sede_destino_id,
                                  remito.sede_origen_id, prestamo.id)
            else:
                prestamo.marcar_listo_para_retiro()
        else:
            self.uow.ejemplares.guardar(ejemplar)
            self._reservas.asignar_ejemplar_liberado(ejemplar)

    def _al_extraviarse(self, remito, ejemplar, prestamo, ctx):
        ejemplar.dar_de_baja()
        if prestamo and prestamo.esta_abierto:
            prestamo.cancelar("Ejemplar extraviado durante el envío")

    def _al_cancelar(self, remito, ejemplar, prestamo, ctx):
        if prestamo and prestamo.esta_abierto:
            prestamo.cancelar(f"Envío cancelado: {ctx.observacion}")
        ejemplar.liberar()
        self.uow.ejemplares.guardar(ejemplar)
        self._reservas.asignar_ejemplar_liberado(ejemplar)
