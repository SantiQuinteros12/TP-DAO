"""Entidad Sede y sus Value Objects Direccion, FranjaHoraria y Horario."""

import json
import re

from domain import validaciones as v
from domain.excepciones import DatoInvalidoError, ReglaNegocioError

PROVINCIAS = (
    "Buenos Aires", "Ciudad Autónoma de Buenos Aires", "Catamarca", "Chaco",
    "Chubut", "Córdoba", "Corrientes", "Entre Ríos", "Formosa", "Jujuy",
    "La Pampa", "La Rioja", "Mendoza", "Misiones", "Neuquén", "Río Negro",
    "Salta", "San Juan", "San Luis", "Santa Cruz", "Santa Fe",
    "Santiago del Estero", "Tierra del Fuego", "Tucumán",
)

DIAS = ("Lun", "Mar", "Mié", "Jue", "Vie", "Sáb", "Dom")


class Direccion:
    """
    Value Object inmutable con la dirección postal de una sede.

    :param calle: calle o avenida
    :param numero: altura (1 a 5 dígitos) o "S/N"
    :param piso_depto: piso, departamento u oficina (opcional)
    :param barrio: barrio (opcional)
    :param ciudad: localidad
    :param provincia: una de las 24 jurisdicciones de Argentina
    :param codigo_postal: 4 dígitos o CPA (opcional)
    """

    CAMPOS = ("calle", "numero", "piso_depto", "barrio", "ciudad",
              "provincia", "codigo_postal")

    def __init__(self, calle, numero, ciudad, provincia, piso_depto="",
                 barrio="", codigo_postal=""):
        calle = v.texto_obligatorio(calle, "La calle", 80)
        if not re.search(r"[A-Za-zÁÉÍÓÚÑáéíóúñ]", calle):
            raise DatoInvalidoError("La calle debe contener letras")
        numero = str(numero or "").strip().upper()
        if numero in ("SN", "S/N", "S N"):
            numero = "S/N"
        elif not re.fullmatch(r"\d{1,5}", numero):
            raise DatoInvalidoError(
                "La altura debe ser un número de hasta 5 dígitos o 'S/N'")
        if provincia not in PROVINCIAS:
            raise DatoInvalidoError(f"Provincia desconocida: '{provincia}'")
        valores = {
            "calle": calle,
            "numero": numero,
            "piso_depto": v.texto_opcional(piso_depto, "Piso/depto", 20),
            "barrio": v.texto_opcional(barrio, "El barrio", 60),
            "ciudad": v.nombre_propio(ciudad, "La ciudad"),
            "provincia": provincia,
            "codigo_postal": v.codigo_postal(codigo_postal),
        }
        for campo, valor in valores.items():
            object.__setattr__(self, campo, valor)

    def __setattr__(self, nombre, valor):
        raise AttributeError("Direccion es inmutable")

    @classmethod
    def desde_dict(cls, datos):
        if isinstance(datos, Direccion):
            return datos
        if not isinstance(datos, dict):
            raise DatoInvalidoError("La dirección es obligatoria")
        return cls(**{c: datos.get(c, "") for c in cls.CAMPOS})

    def a_dict(self):
        return {c: getattr(self, c) for c in self.CAMPOS}

    @property
    def texto(self):
        partes = [f"{self.calle} {self.numero}"]
        if self.piso_depto:
            partes.append(self.piso_depto)
        if self.barrio:
            partes.append(f"B° {self.barrio}")
        partes.append(self.ciudad if self.ciudad == self.provincia
                      else f"{self.ciudad}, {self.provincia}")
        texto = ", ".join(partes)
        return f"{texto} ({self.codigo_postal})" if self.codigo_postal \
            else texto

    def __eq__(self, otra):
        return isinstance(otra, Direccion) and otra.a_dict() == self.a_dict()

    def __hash__(self):
        return hash(tuple(self.a_dict().values()))


class FranjaHoraria:
    """Días de la semana (0 = lunes) con un mismo horario de apertura."""

    def __init__(self, dias, desde, hasta):
        dias = sorted(set(int(d) for d in dias or ()))
        if not dias:
            raise DatoInvalidoError("Cada franja horaria debe tener días")
        if any(d < 0 or d > 6 for d in dias):
            raise DatoInvalidoError("Día de la semana inválido")
        for hora in (desde, hasta):
            if not re.fullmatch(r"([01]\d|2[0-3]):[0-5]\d", str(hora or "")):
                raise DatoInvalidoError(f"Hora inválida: '{hora}' (HH:MM)")
        if desde >= hasta:
            raise DatoInvalidoError(
                f"La hora de apertura ({desde}) debe ser anterior a la de "
                f"cierre ({hasta})")
        self.dias, self.desde, self.hasta = tuple(dias), desde, hasta

    def a_dict(self):
        return {"dias": list(self.dias), "desde": self.desde,
                "hasta": self.hasta}

    @property
    def texto_dias(self):
        d = self.dias
        if len(d) > 2 and d == tuple(range(d[0], d[-1] + 1)):
            return f"{DIAS[d[0]]} a {DIAS[d[-1]]}"
        nombres = [DIAS[i] for i in d]
        return nombres[0] if len(nombres) == 1 else \
            f"{', '.join(nombres[:-1])} y {nombres[-1]}"

    @property
    def texto(self):
        return f"{self.texto_dias} {self.desde} a {self.hasta}"


class Horario:
    """
    Horario de atención como conjunto de franjas. Un mismo día puede tener
    varias franjas (horario cortado) siempre que no se superpongan.
    Un horario vacío significa "sin atención al público".
    """

    def __init__(self, franjas=()):
        self.franjas = tuple(
            f if isinstance(f, FranjaHoraria)
            else FranjaHoraria(f.get("dias"), f.get("desde"), f.get("hasta"))
            for f in franjas or ())
        if len(self.franjas) > 7:
            raise DatoInvalidoError("El horario admite hasta 7 franjas")
        self._validar_superposicion()

    def _validar_superposicion(self):
        for i, a in enumerate(self.franjas):
            for b in self.franjas[i + 1:]:
                comunes = set(a.dias) & set(b.dias)
                if comunes and a.desde < b.hasta and b.desde < a.hasta:
                    dia = DIAS[min(comunes)]
                    raise DatoInvalidoError(
                        f"Franjas superpuestas el {dia}: {a.desde}-{a.hasta} "
                        f"y {b.desde}-{b.hasta}")

    @classmethod
    def desde_json(cls, texto):
        """Reconstruye el horario guardado; textos antiguos quedan vacíos."""
        try:
            return cls(json.loads(texto)) if texto else cls()
        except (ValueError, TypeError, AttributeError, DatoInvalidoError):
            return cls()

    def a_json(self):
        return json.dumps([f.a_dict() for f in self.franjas])

    def a_lista(self):
        return [f.a_dict() for f in self.franjas]

    @property
    def texto(self):
        if not self.franjas:
            return "Sin atención al público"
        orden = sorted(self.franjas, key=lambda f: (f.dias[0], f.desde))
        return " · ".join(f.texto for f in orden)


class Sede:
    """
    Sede de la red de bibliotecas.

    :param nombre: nombre único de la sede
    :param direccion: ``Direccion`` (o dict con sus campos)
    :param telefono: teléfono de contacto
    :param email: correo de contacto
    :param horario: ``Horario`` (o lista de franjas)
    :param activa: False si la sede fue dada de baja
    """

    def __init__(self, nombre, direccion, telefono="", email="", horario=None,
                 activa=True, id=None):
        self.id = id
        self._activa = activa
        self._asignar(nombre, direccion, telefono, email, horario)

    @property
    def activa(self):
        return self._activa

    def _asignar(self, nombre, direccion, telefono, email, horario):
        self.nombre = v.texto_obligatorio(nombre, "El nombre de la sede", 80)
        if len(self.nombre) < 3:
            raise DatoInvalidoError(
                "El nombre de la sede debe tener al menos 3 caracteres")
        self.direccion = Direccion.desde_dict(direccion)
        self.telefono = v.telefono(telefono)
        self.email = v.email(email)
        self.horario = horario if isinstance(horario, Horario) \
            else Horario(horario)

    def actualizar(self, nombre, direccion, telefono, email, horario):
        self._asignar(nombre, direccion, telefono, email, horario)

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
