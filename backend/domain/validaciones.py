"""
Reglas de formato compartidas por las entidades del dominio.

Cada función recibe el valor crudo, lo normaliza y lo devuelve; si no
cumple el formato lanza ``DatoInvalidoError`` con un mensaje listo para
mostrar al usuario. El frontend replica estas mismas reglas para avisar
antes de enviar, pero la validación definitiva vive aquí.
"""

import re

from domain.excepciones import DatoInvalidoError

LETRAS = "A-Za-zÁÉÍÓÚÜÑáéíóúüñ"
_NOMBRE = re.compile(rf"[{LETRAS}]+(?:[ '\-][{LETRAS}]+)*")
_TELEFONO = re.compile(r"\+?[\d\s()\-]+")
_EMAIL = re.compile(r"[^@\s]+@[^@\s]+\.[A-Za-z]{2,}")
_CODIGO_POSTAL = re.compile(r"[A-Za-z]?\d{4}(?:[A-Za-z]{3})?")


def texto_obligatorio(valor, campo, maximo=120):
    valor = " ".join(str(valor or "").split())
    if not valor:
        raise DatoInvalidoError(f"{campo} es obligatorio")
    if len(valor) > maximo:
        raise DatoInvalidoError(f"{campo} admite hasta {maximo} caracteres")
    return valor


def texto_opcional(valor, campo, maximo=120):
    valor = " ".join(str(valor or "").split())
    if len(valor) > maximo:
        raise DatoInvalidoError(f"{campo} admite hasta {maximo} caracteres")
    return valor


def nombre_propio(valor, campo, obligatorio=True):
    """Sólo letras (con tildes), espacios, apóstrofo y guion; sin números."""
    valor = " ".join(str(valor or "").split())
    if not valor:
        if obligatorio:
            raise DatoInvalidoError(f"{campo} es obligatorio")
        return valor
    if not _NOMBRE.fullmatch(valor):
        raise DatoInvalidoError(
            f"{campo} sólo puede contener letras, espacios, apóstrofos o "
            "guiones")
    if len(valor) < 2 or len(valor) > 60:
        raise DatoInvalidoError(f"{campo} debe tener entre 2 y 60 caracteres")
    return valor


def telefono(valor, obligatorio=False):
    """Dígitos con separadores opcionales (+, espacios, guiones, paréntesis)."""
    valor = " ".join(str(valor or "").split())
    if not valor:
        if obligatorio:
            raise DatoInvalidoError("El teléfono es obligatorio")
        return valor
    digitos = re.sub(r"\D", "", valor)
    if not _TELEFONO.fullmatch(valor) or valor.count("+") > 1:
        raise DatoInvalidoError(
            "El teléfono sólo puede contener números, espacios, guiones, "
            "paréntesis y un '+' inicial")
    if not 7 <= len(digitos) <= 15:
        raise DatoInvalidoError("El teléfono debe tener entre 7 y 15 dígitos")
    return valor


def email(valor, obligatorio=False):
    valor = str(valor or "").strip().lower()
    if not valor:
        if obligatorio:
            raise DatoInvalidoError("El email es obligatorio")
        return valor
    if len(valor) > 120 or not _EMAIL.fullmatch(valor):
        raise DatoInvalidoError(f"El email '{valor}' no tiene un formato válido")
    return valor


def codigo_postal(valor):
    """CPA argentino (X5000ABC) o código numérico de 4 dígitos; opcional."""
    valor = str(valor or "").strip().upper()
    if valor and not _CODIGO_POSTAL.fullmatch(valor):
        raise DatoInvalidoError(
            "El código postal debe tener 4 dígitos (ej. 5000) o formato CPA "
            "(ej. X5000ABC)")
    return valor
