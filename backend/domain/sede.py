"""Entidad Sede: cada biblioteca que integra la red."""

from domain.excepciones import DatoInvalidoError, ReglaNegocioError


class Sede:
    """
    Sede de la red de bibliotecas.

    :param nombre: nombre único de la sede
    :param direccion: dirección postal
    :param telefono: teléfono de contacto
    :param email: correo de contacto
    :param horario: horario de atención (texto libre, ej. "Lun a Vie 8-20")
    :param activa: False si la sede fue dada de baja
    """

    def __init__(self, nombre, direccion, telefono="", email="", horario="",
                 activa=True, id=None):
        self.id = id
        self.nombre = nombre
        self.direccion = direccion
        self.telefono = telefono
        self.email = email
        self.horario = horario
        self._activa = activa
        self._validar()

    @property
    def activa(self):
        return self._activa

    def _validar(self):
        if not self.nombre or not self.nombre.strip():
            raise DatoInvalidoError("El nombre de la sede es obligatorio")
        if not self.direccion or not self.direccion.strip():
            raise DatoInvalidoError("La dirección de la sede es obligatoria")
        if self.email and "@" not in self.email:
            raise DatoInvalidoError("El email de la sede no es válido")
        self.nombre = self.nombre.strip()

    def actualizar(self, nombre, direccion, telefono, email, horario):
        self.nombre = nombre
        self.direccion = direccion
        self.telefono = telefono
        self.email = email
        self.horario = horario
        self._validar()

    def dar_de_baja(self):
        if not self._activa:
            raise ReglaNegocioError(f"La sede '{self.nombre}' ya está dada de baja")
        self._activa = False

    def reactivar(self):
        if self._activa:
            raise ReglaNegocioError(f"La sede '{self.nombre}' ya está activa")
        self._activa = True

    def verificar_operativa(self):
        """
        Valida que se puedan iniciar operaciones (préstamos, reservas o
        envíos) hacia o desde esta sede.

        :raises ReglaNegocioError: si la sede está dada de baja
        """
        if not self._activa:
            raise ReglaNegocioError(
                f"La sede '{self.nombre}' está dada de baja: no se pueden "
                "iniciar préstamos, reservas ni envíos hacia o desde ella")
