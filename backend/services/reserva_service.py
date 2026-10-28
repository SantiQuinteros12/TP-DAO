"""Caso de uso: gestionar reservas."""

from domain.enums import EstadoReserva
from domain.eventos import ReservaDisponible
from domain.excepciones import DuplicadoError, ReglaNegocioError
from domain.libro import ISBN
from domain.reserva import Reserva
from services.base import ServicioBase


class ReservaService(ServicioBase):

    def obtener(self, reserva_id):
        return self._requerir(self.uow.reservas, reserva_id, "Reserva")

    def crear(self, socio_id, isbn, sede_id):
        """
        Registra la reserva y, si hay un ejemplar disponible en la sede, se
        lo asigna inmediatamente; si no, queda en cola (FIFO).
        """
        isbn = ISBN(isbn).valor
        socio = self._requerir(self.uow.socios, socio_id, "Socio")
        sede = self._requerir(self.uow.sedes, sede_id, "Sede")
        self._requerir(self.uow.libros, isbn, "Libro")
        socio.verificar_puede_operar()
        sede.verificar_operativa()
        if self.uow.reservas.activa_de_socio(socio_id, isbn):
            raise DuplicadoError(
                "El socio ya tiene una reserva activa para este libro")
        if not self.uow.ejemplares.listar(isbn=isbn, sede_id=sede_id):
            raise ReglaNegocioError(
                f"La sede '{sede.nombre}' no posee ejemplares de este libro; "
                "solicite un préstamo interbibliotecario")
        reserva = self.uow.reservas.guardar(
            Reserva(socio_id, isbn, sede_id, self.reloj.hoy()))
        ejemplar = self.uow.ejemplares.buscar_disponible(isbn, sede_id)
        if ejemplar:
            self.asignar_ejemplar_liberado(ejemplar)
        return self.obtener(reserva.id)

    def cancelar(self, reserva_id):
        reserva = self.obtener(reserva_id)
        estaba_asignada = reserva.estado == EstadoReserva.DISPONIBLE
        reserva.cancelar()
        self.uow.reservas.guardar(reserva)
        if estaba_asignada:
            self._liberar_ejemplar(reserva.ejemplar_id)
        return reserva

    def procesar_vencidas(self):
        """
        Vence las reservas cuyo plazo de retiro expiró y reasigna los
        ejemplares liberados a la siguiente reserva en cola.

        :return: cantidad de reservas vencidas
        """
        hoy = self.reloj.hoy()
        vencidas = [r for r in self.uow.reservas.listar(
            estado=EstadoReserva.DISPONIBLE) if r.expiro(hoy)]
        for reserva in vencidas:
            reserva.vencer()
            self.uow.reservas.guardar(reserva)
            self._liberar_ejemplar(reserva.ejemplar_id)
        return len(vencidas)

    def asignar_ejemplar_liberado(self, ejemplar):
        """
        Punto único usado por todos los servicios cuando un ejemplar queda
        DISPONIBLE en su sede: lo asigna a la reserva más antigua en cola.

        :return: la reserva asignada o None
        """
        if not (ejemplar.esta_disponible and ejemplar.esta_en_su_sede):
            return None
        for reserva in self.uow.reservas.pendientes(ejemplar.isbn,
                                                    ejemplar.sede_id):
            socio = self.uow.socios.obtener(reserva.socio_id)
            if not socio.habilitado:
                continue
            reserva.asignar_ejemplar(ejemplar.id, self.reloj.hoy())
            ejemplar.reservar()
            self.uow.reservas.guardar(reserva)
            self.uow.ejemplares.guardar(ejemplar)
            self._publicar(ReservaDisponible(
                ocurrido_en=self.reloj.ahora(), reserva_id=reserva.id,
                socio_id=reserva.socio_id, isbn=reserva.isbn,
                sede_id=reserva.sede_id))
            return reserva
        return None

    def _liberar_ejemplar(self, ejemplar_id):
        ejemplar = self.uow.ejemplares.obtener(ejemplar_id)
        ejemplar.liberar()
        self.uow.ejemplares.guardar(ejemplar)
        self.asignar_ejemplar_liberado(ejemplar)
