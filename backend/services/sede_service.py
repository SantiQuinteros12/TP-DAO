"""Caso de uso: administrar sedes de la red."""

from domain.excepciones import DuplicadoError, ReglaNegocioError
from domain.sede import Sede
from services.base import ServicioBase


class SedeService(ServicioBase):

    def listar(self, incluir_bajas=True):
        return self.uow.sedes.listar(incluir_bajas)

    def obtener(self, sede_id):
        return self._requerir(self.uow.sedes, sede_id, "Sede")

    def crear(self, nombre, direccion, telefono="", email="", horario=()):
        sede = Sede(nombre, direccion, telefono, email, horario)
        self._validar_nombre_unico(sede.nombre)
        return self.uow.sedes.guardar(sede)

    def actualizar(self, sede_id, nombre, direccion, telefono, email,
                   horario):
        sede = self.obtener(sede_id)
        self._validar_nombre_unico(nombre, excluir_id=sede_id)
        sede.actualizar(nombre, direccion, telefono, email, horario)
        return self.uow.sedes.guardar(sede)

    def dar_de_baja(self, sede_id):
        """
        Una sede sólo puede darse de baja si no tiene operaciones en curso;
        de lo contrario quedarían ejemplares sin poder retornar.
        """
        sede = self.obtener(sede_id)
        pendientes = {
            "remitos en curso": self.uow.remitos.contar_en_curso_de_sede(
                sede_id),
            "préstamos abiertos": self.uow.prestamos.contar_abiertos_de_sede(
                sede_id),
            "reservas activas": self.uow.reservas.contar_activas_de_sede(
                sede_id),
        }
        bloqueos = [f"{n} {d}" for d, n in pendientes.items() if n]
        if bloqueos:
            raise ReglaNegocioError(
                f"No se puede dar de baja la sede '{sede.nombre}': tiene "
                + ", ".join(bloqueos))
        sede.dar_de_baja()
        return self.uow.sedes.guardar(sede)

    def reactivar(self, sede_id):
        sede = self.obtener(sede_id)
        sede.reactivar()
        return self.uow.sedes.guardar(sede)

    def _validar_nombre_unico(self, nombre, excluir_id=None):
        existente = self.uow.sedes.obtener_por_nombre(nombre or "")
        if existente and existente.id != excluir_id:
            raise DuplicadoError(f"Ya existe una sede llamada '{nombre}'")
