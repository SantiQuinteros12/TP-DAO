"""
Patrón REPOSITORY: contratos de acceso a datos.

El dominio y los servicios dependen de estas abstracciones (Dependency
Inversion); la implementación concreta (SQLite) vive en
``infrastructure``. Cambiar de motor de base de datos sólo requiere una
nueva implementación de estas interfaces.
"""

from abc import ABC, abstractmethod


class Repositorio(ABC):
    """Operaciones comunes a todos los repositorios."""

    @abstractmethod
    def obtener(self, id):
        """:return: la entidad o None si no existe"""

    @abstractmethod
    def guardar(self, entidad):
        """Inserta o actualiza. Asigna ``id`` si la entidad es nueva."""


class RepositorioSedes(Repositorio):

    @abstractmethod
    def listar(self, incluir_bajas=True):
        pass

    @abstractmethod
    def obtener_por_nombre(self, nombre):
        pass


class RepositorioSocios(Repositorio):

    @abstractmethod
    def obtener_por_documento(self, documento):
        pass

    @abstractmethod
    def listar(self, texto=None, habilitado=None):
        pass


class RepositorioLibros(Repositorio):
    """La clave de un libro es su ISBN normalizado."""

    @abstractmethod
    def listar(self, texto=None):
        pass

    @abstractmethod
    def insertar(self, libro):
        pass


class RepositorioEjemplares(Repositorio):

    @abstractmethod
    def obtener_por_codigo(self, codigo_inventario):
        pass

    @abstractmethod
    def listar(self, isbn=None, sede_id=None, estado=None):
        pass

    @abstractmethod
    def buscar_disponible(self, isbn, sede_id):
        """Primer ejemplar DISPONIBLE del libro ubicado en su sede."""


class RepositorioPrestamos(Repositorio):

    @abstractmethod
    def listar(self, estado=None, socio_id=None, sede_id=None):
        pass

    @abstractmethod
    def abiertos_de_socio(self, socio_id):
        pass

    @abstractmethod
    def abierto_de_ejemplar(self, ejemplar_id):
        pass

    @abstractmethod
    def contar_abiertos_de_sede(self, sede_id):
        pass


class RepositorioReservas(Repositorio):

    @abstractmethod
    def listar(self, estado=None, socio_id=None, sede_id=None):
        pass

    @abstractmethod
    def activa_de_socio(self, socio_id, isbn):
        pass

    @abstractmethod
    def pendientes(self, isbn, sede_id):
        """Reservas PENDIENTES ordenadas por antigüedad (cola FIFO)."""

    @abstractmethod
    def contar_activas_de_sede(self, sede_id):
        pass


class RepositorioRemitos(Repositorio):

    @abstractmethod
    def listar(self, estado=None, sede_id=None, tipo=None):
        pass

    @abstractmethod
    def en_curso_de_ejemplar(self, ejemplar_id):
        pass

    @abstractmethod
    def de_prestamo(self, prestamo_id):
        pass

    @abstractmethod
    def contar_en_curso_de_sede(self, sede_id):
        pass


class RepositorioNotificaciones(Repositorio):

    @abstractmethod
    def listar(self, socio_id, solo_no_leidas=False):
        pass


class UnidadDeTrabajo(ABC):
    """
    Agrupa los repositorios de una operación y define su transacción:
    todo se confirma junto o nada (atomicidad de los casos de uso).
    """

    sedes: RepositorioSedes
    socios: RepositorioSocios
    libros: RepositorioLibros
    ejemplares: RepositorioEjemplares
    prestamos: RepositorioPrestamos
    reservas: RepositorioReservas
    remitos: RepositorioRemitos
    notificaciones: RepositorioNotificaciones

    @abstractmethod
    def confirmar(self):
        pass

    @abstractmethod
    def revertir(self):
        pass

    def __enter__(self):
        return self

    def __exit__(self, tipo_exc, exc, tb):
        if tipo_exc is None:
            self.confirmar()
        else:
            self.revertir()
        self.cerrar()
        return False

    def cerrar(self):
        pass
