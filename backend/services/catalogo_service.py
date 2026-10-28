"""Caso de uso: administrar catálogo de libros y ejemplares físicos."""

from domain.ejemplar import Ejemplar
from domain.excepciones import DuplicadoError, ReglaNegocioError
from domain.libro import ISBN, Libro
from services.base import ServicioBase
from services.reserva_service import ReservaService


class CatalogoService(ServicioBase):

    def __init__(self, uow, reloj, publicador=None):
        super().__init__(uow, reloj, publicador)
        self._reservas = ReservaService(uow, reloj, self.publicador)

    # --- libros ----------------------------------------------------------
    def listar_libros(self, texto=None):
        return self.uow.libros.listar(texto)

    def obtener_libro(self, isbn):
        return self._requerir(self.uow.libros, ISBN(isbn).valor, "Libro")

    def crear_libro(self, isbn, titulo, autor, editorial="",
                    anio_publicacion=None, genero=""):
        libro = Libro(isbn, titulo, autor, editorial, anio_publicacion, genero)
        if self.uow.libros.obtener(libro.isbn):
            raise DuplicadoError(
                f"Ya existe un libro con ISBN {libro.isbn} en el catálogo")
        return self.uow.libros.insertar(libro)

    def actualizar_libro(self, isbn, titulo, autor, editorial,
                         anio_publicacion, genero):
        libro = self.obtener_libro(isbn)
        libro.actualizar(titulo, autor, editorial, anio_publicacion, genero)
        return self.uow.libros.guardar(libro)

    # --- ejemplares ------------------------------------------------------
    def obtener_ejemplar(self, ejemplar_id):
        return self._requerir(self.uow.ejemplares, ejemplar_id, "Ejemplar")

    def crear_ejemplar(self, isbn, sede_id, codigo_inventario=None):
        """
        Da de alta un ejemplar físico asignándolo a una sede.
        Si no se indica código de inventario se genera uno correlativo.
        """
        libro = self.obtener_libro(isbn)
        sede = self._requerir(self.uow.sedes, sede_id, "Sede")
        sede.verificar_operativa()
        codigo = codigo_inventario or self._generar_codigo(libro.isbn, sede)
        if self.uow.ejemplares.obtener_por_codigo(codigo):
            raise DuplicadoError(
                f"Ya existe un ejemplar con código de inventario {codigo}")
        ejemplar = self.uow.ejemplares.guardar(
            Ejemplar(libro.isbn, sede.id, codigo))
        self._reservas.asignar_ejemplar_liberado(ejemplar)
        return ejemplar

    def dar_de_baja_ejemplar(self, ejemplar_id):
        ejemplar = self.obtener_ejemplar(ejemplar_id)
        if self.uow.prestamos.abierto_de_ejemplar(ejemplar_id):
            raise ReglaNegocioError(
                "El ejemplar tiene un préstamo abierto: no puede darse de baja")
        if self.uow.remitos.en_curso_de_ejemplar(ejemplar_id):
            raise ReglaNegocioError(
                "El ejemplar tiene un remito en curso: no puede darse de baja")
        ejemplar.dar_de_baja()
        return self.uow.ejemplares.guardar(ejemplar)

    def reparar_ejemplar(self, ejemplar_id):
        """Reincorpora un ejemplar DANADO tras su reparación."""
        ejemplar = self.obtener_ejemplar(ejemplar_id)
        if self.uow.remitos.en_curso_de_ejemplar(ejemplar_id):
            raise ReglaNegocioError(
                "El ejemplar debe volver a su sede antes de reincorporarse")
        ejemplar.reparar()
        self.uow.ejemplares.guardar(ejemplar)
        self._reservas.asignar_ejemplar_liberado(ejemplar)
        return ejemplar

    def _generar_codigo(self, isbn, sede):
        prefijo = "".join(p[0] for p in sede.nombre.split()[:3]).upper()
        n = len(self.uow.ejemplares.listar(isbn=isbn)) + 1
        while True:
            codigo = f"{prefijo}{sede.id}-{isbn[-5:]}-{n:03d}"
            if not self.uow.ejemplares.obtener_por_codigo(codigo):
                return codigo
            n += 1
