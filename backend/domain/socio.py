"""Entidad Socio."""

import re

from domain.excepciones import DatoInvalidoError, ReglaNegocioError


class Socio:
    """
    Socio de la red de bibliotecas.

    :param documento: DNI (7 u 8 dígitos), único en el sistema
    :param habilitado: False si el socio está inhabilitado para operar
    :param motivo_inhabilitacion: causa registrada al inhabilitarlo
    """

    def __init__(self, nombre, apellido, documento, email="", telefono="",
                 fecha_alta=None, habilitado=True, motivo_inhabilitacion=None,
                 id=None):
        self.id = id
        self.nombre = nombre
        self.apellido = apellido
        self.documento = documento
        self.email = email
        self.telefono = telefono
        self.fecha_alta = fecha_alta
        self._habilitado = habilitado
        self._motivo_inhabilitacion = motivo_inhabilitacion
        self._validar()

    @property
    def habilitado(self):
        return self._habilitado

    @property
    def motivo_inhabilitacion(self):
        return self._motivo_inhabilitacion

    @property
    def nombre_completo(self):
        return f"{self.apellido}, {self.nombre}"

    def _validar(self):
        if not (self.nombre or "").strip() or not (self.apellido or "").strip():
            raise DatoInvalidoError("Nombre y apellido son obligatorios")
        self.documento = re.sub(r"[.\s]", "", str(self.documento or ""))
        if not re.fullmatch(r"\d{7,8}", self.documento):
            raise DatoInvalidoError("El documento debe tener 7 u 8 dígitos")
        if self.email and "@" not in self.email:
            raise DatoInvalidoError("El email del socio no es válido")

    def actualizar(self, nombre, apellido, documento, email, telefono):
        self.nombre = nombre
        self.apellido = apellido
        self.documento = documento
        self.email = email
        self.telefono = telefono
        self._validar()

    def inhabilitar(self, motivo):
        if not self._habilitado:
            raise ReglaNegocioError("El socio ya se encuentra inhabilitado")
        if not (motivo or "").strip():
            raise DatoInvalidoError("Debe indicar el motivo de la inhabilitación")
        self._habilitado = False
        self._motivo_inhabilitacion = motivo.strip()

    def habilitar(self):
        if self._habilitado:
            raise ReglaNegocioError("El socio ya se encuentra habilitado")
        self._habilitado = True
        self._motivo_inhabilitacion = None

    def verificar_puede_operar(self):
        """
        :raises ReglaNegocioError: si el socio está inhabilitado
        """
        if not self._habilitado:
            raise ReglaNegocioError(
                f"El socio {self.nombre_completo} está inhabilitado "
                f"({self._motivo_inhabilitacion})")
