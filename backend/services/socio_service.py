"""Caso de uso: administrar socios."""

from domain.excepciones import DuplicadoError
from domain.socio import Socio
from services.base import ServicioBase


class SocioService(ServicioBase):

    def listar(self, texto=None, habilitado=None):
        return self.uow.socios.listar(texto, habilitado)

    def obtener(self, socio_id):
        return self._requerir(self.uow.socios, socio_id, "Socio")

    def crear(self, nombre, apellido, documento, email="", telefono=""):
        socio = Socio(nombre, apellido, documento, email, telefono,
                      fecha_alta=self.reloj.hoy())
        self._validar_documento_unico(socio.documento)
        return self.uow.socios.guardar(socio)

    def actualizar(self, socio_id, nombre, apellido, documento, email,
                   telefono):
        socio = self.obtener(socio_id)
        socio.actualizar(nombre, apellido, documento, email, telefono)
        self._validar_documento_unico(socio.documento, excluir_id=socio_id)
        return self.uow.socios.guardar(socio)

    def inhabilitar(self, socio_id, motivo):
        socio = self.obtener(socio_id)
        socio.inhabilitar(motivo)
        return self.uow.socios.guardar(socio)

    def habilitar(self, socio_id):
        socio = self.obtener(socio_id)
        socio.habilitar()
        return self.uow.socios.guardar(socio)

    def notificaciones(self, socio_id, solo_no_leidas=False):
        self.obtener(socio_id)
        return self.uow.notificaciones.listar(socio_id, solo_no_leidas)

    def marcar_notificaciones_leidas(self, socio_id):
        for notificacion in self.notificaciones(socio_id, True):
            notificacion.marcar_leida()
            self.uow.notificaciones.guardar(notificacion)

    def _validar_documento_unico(self, documento, excluir_id=None):
        existente = self.uow.socios.obtener_por_documento(documento)
        if existente and existente.id != excluir_id:
            raise DuplicadoError(
                f"Ya existe un socio con documento {documento}")
