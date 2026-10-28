"""Caso de uso: solicitudes de préstamo, entregas y devoluciones."""

from domain.enums import EstadoPrestamo, EstadoReserva, TipoRemito
from domain.eventos import PrestamoDevuelto
from domain.excepciones import ReglaNegocioError, TransicionInvalidaError
from domain.fabricas import creador_para
from services.base import ServicioBase
from services.logistica_service import LogisticaService
from services.reserva_service import ReservaService

MAX_PRESTAMOS_ABIERTOS = 3


class PrestamoService(ServicioBase):

    def __init__(self, uow, reloj, publicador=None):
        super().__init__(uow, reloj, publicador)
        self._logistica = LogisticaService(uow, reloj, self.publicador)
        self._reservas = ReservaService(uow, reloj, self.publicador)

    def obtener(self, prestamo_id):
        return self._requerir(self.uow.prestamos, prestamo_id, "Préstamo")

    def solicitar(self, socio_id, ejemplar_id, sede_origen_id,
                  sede_destino_id, reserva_id=None):
        """
        Registra un préstamo local (origen == destino) o interbibliotecario.
        El tipo concreto lo resuelve el Factory Method; para los
        interbibliotecarios se genera además el remito de envío.
        """
        socio = self._requerir(self.uow.socios, socio_id, "Socio")
        ejemplar = self._requerir(self.uow.ejemplares, ejemplar_id,
                                  "Ejemplar")
        origen = self._requerir(self.uow.sedes, sede_origen_id, "Sede")
        destino = self._requerir(self.uow.sedes, sede_destino_id, "Sede")
        self._validar_cupo_socio(socio)

        creador = creador_para(origen.id, destino.id)
        prestamo = creador.crear(socio, ejemplar, origen, destino,
                                 self.reloj.hoy(), reserva_id)
        self.uow.prestamos.guardar(prestamo)
        self.uow.ejemplares.guardar(ejemplar)
        if prestamo.es_interbibliotecario:
            self._logistica.crear_remito(TipoRemito.ENVIO, ejemplar,
                                         origen.id, destino.id, prestamo.id)
        return prestamo

    def concretar_reserva(self, reserva_id):
        """Convierte una reserva DISPONIBLE en un préstamo local."""
        reserva = self._reservas.obtener(reserva_id)
        if reserva.estado != EstadoReserva.DISPONIBLE:
            raise TransicionInvalidaError(
                "Sólo se pueden concretar reservas con ejemplar asignado")
        reserva.cumplir(self.reloj.hoy())
        prestamo = self.solicitar(reserva.socio_id, reserva.ejemplar_id,
                                  reserva.sede_id, reserva.sede_id,
                                  reserva_id=reserva.id)
        self.uow.reservas.guardar(reserva)
        return prestamo

    def entregar(self, prestamo_id):
        """El socio retira en sede destino un ejemplar interbibliotecario."""
        prestamo = self.obtener(prestamo_id)
        socio = self.uow.socios.obtener(prestamo.socio_id)
        socio.verificar_puede_operar()
        self.uow.sedes.obtener(prestamo.sede_destino_id).verificar_operativa()
        ejemplar = self.uow.ejemplares.obtener(prestamo.ejemplar_id)
        prestamo.activar(self.reloj.hoy())
        ejemplar.prestar()
        self.uow.prestamos.guardar(prestamo)
        self.uow.ejemplares.guardar(ejemplar)
        return prestamo

    def cancelar(self, prestamo_id, motivo):
        """
        Cancela un préstamo aún no entregado. Si el ejemplar no salió, se
        anula el envío; si ya está en la sede destino, se genera el retorno.
        """
        prestamo = self.obtener(prestamo_id)
        if not motivo:
            raise ReglaNegocioError("Debe indicar el motivo de cancelación")
        envio = next((r for r in self.uow.remitos.de_prestamo(prestamo.id)
                      if r.tipo == TipoRemito.ENVIO), None)

        if prestamo.estado == EstadoPrestamo.PENDIENTE_ENVIO:
            if envio is None or "cancelar" not in envio.acciones_disponibles:
                raise ReglaNegocioError(
                    "El ejemplar ya fue despachado: no puede cancelarse hasta "
                    "que se reciba en destino")
            # La cancelación del remito cancela el préstamo y libera el
            # ejemplar (LogisticaService._al_cancelar).
            self._logistica.operar(envio.id, "cancelar",
                                   observacion=motivo)
            return self.obtener(prestamo_id)

        prestamo.cancelar(motivo)
        self.uow.prestamos.guardar(prestamo)
        ejemplar = self.uow.ejemplares.obtener(prestamo.ejemplar_id)
        self._logistica.crear_remito(TipoRemito.RETORNO, ejemplar,
                                     prestamo.sede_destino_id,
                                     prestamo.sede_origen_id, prestamo.id)
        return prestamo

    def registrar_devolucion(self, prestamo_id, condicion, observaciones=""):
        """
        Registra la devolución evaluando el estado físico del material.
        Calcula la multa (Strategy) y, si el préstamo fue interbibliotecario,
        genera el remito de retorno a la sede propietaria.
        """
        prestamo = self.obtener(prestamo_id)
        ejemplar = self.uow.ejemplares.obtener(prestamo.ejemplar_id)
        multa = prestamo.registrar_devolucion(self.reloj.hoy(), condicion,
                                              observaciones)
        ejemplar.registrar_devolucion(
            condicion, queda_retenido=prestamo.es_interbibliotecario)
        self.uow.prestamos.guardar(prestamo)
        self.uow.ejemplares.guardar(ejemplar)

        if prestamo.es_interbibliotecario:
            self._logistica.crear_remito(TipoRemito.RETORNO, ejemplar,
                                         prestamo.sede_destino_id,
                                         prestamo.sede_origen_id, prestamo.id)
        else:
            self._reservas.asignar_ejemplar_liberado(ejemplar)

        self._publicar(PrestamoDevuelto(
            ocurrido_en=self.reloj.ahora(), prestamo_id=prestamo.id,
            socio_id=prestamo.socio_id, multa=multa))
        return prestamo

    def evaluar_elegibilidad(self, socio_id):
        """
        Indica si el socio puede solicitar un préstamo ahora y, si no, por
        qué. Permite avisar en la UI antes de completar la solicitud; las
        mismas reglas se vuelven a aplicar al registrarla.
        """
        socio = self._requerir(self.uow.socios, socio_id, "Socio")
        abiertos = self.uow.prestamos.abiertos_de_socio(socio.id)
        vencidos = [p for p in abiertos if p.esta_vencido(self.reloj.hoy())]
        impedimentos = []
        if not socio.habilitado:
            impedimentos.append(
                f"Está inhabilitado ({socio.motivo_inhabilitacion})")
        impedimentos += self._impedimentos_de_cupo(abiertos, vencidos)
        return {
            "socio_id": socio.id,
            "socio": socio.nombre_completo,
            "puede_solicitar": not impedimentos,
            "impedimentos": impedimentos,
            "prestamos_abiertos": len(abiertos),
            "prestamos_vencidos": len(vencidos),
            "maximo_prestamos": MAX_PRESTAMOS_ABIERTOS,
        }

    @staticmethod
    def _impedimentos_de_cupo(abiertos, vencidos):
        impedimentos = []
        if vencidos:
            impedimentos.append(
                f"El socio tiene {len(vencidos)} préstamo(s) vencido(s): "
                "debe regularizarlos antes de solicitar otro")
        if len(abiertos) >= MAX_PRESTAMOS_ABIERTOS:
            impedimentos.append(
                f"El socio alcanzó el máximo de {MAX_PRESTAMOS_ABIERTOS} "
                "préstamos abiertos")
        return impedimentos

    def _validar_cupo_socio(self, socio):
        abiertos = self.uow.prestamos.abiertos_de_socio(socio.id)
        vencidos = [p for p in abiertos if p.esta_vencido(self.reloj.hoy())]
        impedimentos = self._impedimentos_de_cupo(abiertos, vencidos)
        if impedimentos:
            raise ReglaNegocioError(impedimentos[0])
