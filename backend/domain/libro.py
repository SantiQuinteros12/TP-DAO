"""Entidad Libro (obra del catálogo) y Value Object ISBN."""

import re

from domain.excepciones import DatoInvalidoError


class ISBN:
    """
    Value Object inmutable que normaliza y valida un ISBN-10 o ISBN-13
    (incluye verificación del dígito de control).
    """

    __slots__ = ("_valor",)

    def __init__(self, valor):
        normalizado = re.sub(r"[-\s]", "", str(valor or "")).upper()
        if not self._es_valido(normalizado):
            raise DatoInvalidoError(f"ISBN inválido: '{valor}'")
        object.__setattr__(self, "_valor", normalizado)

    def __setattr__(self, nombre, valor):
        raise AttributeError("ISBN es inmutable")

    @property
    def valor(self):
        return self._valor

    @staticmethod
    def _es_valido(isbn):
        if re.fullmatch(r"\d{9}[\dX]", isbn):
            total = sum((10 - i) * (10 if c == "X" else int(c))
                        for i, c in enumerate(isbn))
            return total % 11 == 0
        if re.fullmatch(r"\d{13}", isbn):
            total = sum(int(c) * (1 if i % 2 == 0 else 3)
                        for i, c in enumerate(isbn))
            return total % 10 == 0
        return False

    def __eq__(self, otro):
        return isinstance(otro, ISBN) and otro._valor == self._valor

    def __hash__(self):
        return hash(self._valor)

    def __str__(self):
        return self._valor


class Libro:
    """
    Obra del catálogo. Los ejemplares físicos referencian al libro por ISBN.
    """

    def __init__(self, isbn, titulo, autor, editorial="", anio_publicacion=None,
                 genero=""):
        self._isbn = isbn if isinstance(isbn, ISBN) else ISBN(isbn)
        self.titulo = titulo
        self.autor = autor
        self.editorial = editorial
        self.anio_publicacion = anio_publicacion
        self.genero = genero
        self._validar()

    @property
    def isbn(self):
        return self._isbn.valor

    def _validar(self):
        if not (self.titulo or "").strip():
            raise DatoInvalidoError("El título es obligatorio")
        if not (self.autor or "").strip():
            raise DatoInvalidoError("El autor es obligatorio")
        if self.anio_publicacion is not None and not (
                0 < int(self.anio_publicacion) <= 2100):
            raise DatoInvalidoError("Año de publicación inválido")

    def actualizar(self, titulo, autor, editorial, anio_publicacion, genero):
        self.titulo = titulo
        self.autor = autor
        self.editorial = editorial
        self.anio_publicacion = anio_publicacion
        self.genero = genero
        self._validar()
