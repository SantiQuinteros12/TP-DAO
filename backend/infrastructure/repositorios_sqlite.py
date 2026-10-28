"""
Implementación SQLite de los repositorios (patrón Repository).

Cada repositorio traduce filas <-> entidades del dominio (Data Mapper); el
resto del sistema nunca ve SQL ni objetos ``sqlite3.Row``.
"""

from abc import abstractmethod
from datetime import date, datetime

from domain.ejemplar import Ejemplar
from domain.enums import EstadoEjemplar, EstadoPrestamo, EstadoReserva
from domain.libro import Libro
from domain.notificacion import Notificacion
from domain.prestamo import Prestamo
from domain.remito import ESTADOS_EN_CURSO, MovimientoRemito, Remito
from domain.repositorios import (RepositorioEjemplares, RepositorioLibros,
                                 RepositorioNotificaciones,
                                 RepositorioPrestamos, RepositorioRemitos,
                                 RepositorioReservas, RepositorioSedes,
                                 RepositorioSocios, UnidadDeTrabajo)
from domain.reserva import Reserva
from domain.sede import Direccion, Horario, Sede
from domain.socio import Socio
from infrastructure.database import conectar

ABIERTOS = tuple(e.value for e in (EstadoPrestamo.PENDIENTE_ENVIO,
                                   EstadoPrestamo.LISTO_PARA_RETIRO,
                                   EstadoPrestamo.ACTIVO))


# --- conversión de tipos ------------------------------------------------
def a_texto(valor):
    if valor is None:
        return None
    if isinstance(valor, (date, datetime)):
        return valor.isoformat()
    return getattr(valor, "value", valor)


def a_fecha(texto):
    return date.fromisoformat(texto) if texto else None


def a_fecha_hora(texto):
    return datetime.fromisoformat(texto) if texto else None


def marcadores(valores):
    return ", ".join("?" for _ in valores)


class RepositorioSQLite:
    """Base genérica: CRUD por ``id`` y mapeo delegado a las subclases."""

    tabla = None
    columnas = ()

    def __init__(self, conexion):
        self._cx = conexion

    def _uno(self, sql, parametros=()):
        fila = self._cx.execute(sql, parametros).fetchone()
        return self._a_entidad(fila) if fila else None

    def _varios(self, sql, parametros=()):
        return [self._a_entidad(f)
                for f in self._cx.execute(sql, parametros).fetchall()]

    def _escalar(self, sql, parametros=()):
        return self._cx.execute(sql, parametros).fetchone()[0]

    @abstractmethod
    def _a_entidad(self, fila):
        pass

    @abstractmethod
    def _a_fila(self, entidad):
        """:return: tupla de valores en el orden de ``columnas``"""

    def obtener(self, id):
        return self._uno(f"SELECT * FROM {self.tabla} WHERE id = ?", (id,))

    def guardar(self, entidad):
        valores = tuple(a_texto(v) for v in self._a_fila(entidad))
        if entidad.id is None:
            cursor = self._cx.execute(
                f"INSERT INTO {self.tabla} ({', '.join(self.columnas)}) "
                f"VALUES ({marcadores(self.columnas)})", valores)
            entidad.id = cursor.lastrowid
        else:
            asignaciones = ", ".join(f"{c} = ?" for c in self.columnas)
            self._cx.execute(
                f"UPDATE {self.tabla} SET {asignaciones} WHERE id = ?",
                valores + (entidad.id,))
        return entidad


class SedesSQLite(RepositorioSQLite, RepositorioSedes):
    tabla = "sedes"
    columnas = ("nombre", "direccion") + Direccion.CAMPOS + (
        "telefono", "email", "horario", "activa")

    def _a_entidad(self, f):
        direccion = Direccion.desde_dict(
            {c: f[c] for c in Direccion.CAMPOS})
        return Sede(f["nombre"], direccion, f["telefono"], f["email"],
                    Horario.desde_json(f["horario"]), bool(f["activa"]),
                    id=f["id"])

    def _a_fila(self, s):
        return ((s.nombre, s.direccion.texto)
                + tuple(s.direccion.a_dict().values())
                + (s.telefono, s.email, s.horario.a_json(), int(s.activa)))

    def listar(self, incluir_bajas=True):
        filtro = "" if incluir_bajas else "WHERE activa = 1"
        return self._varios(f"SELECT * FROM sedes {filtro} ORDER BY nombre")

    def obtener_por_nombre(self, nombre):
        return self._uno("SELECT * FROM sedes WHERE nombre = ?",
                         (nombre.strip(),))


class SociosSQLite(RepositorioSQLite, RepositorioSocios):
    tabla = "socios"
    columnas = ("nombre", "apellido", "documento", "email", "telefono",
                "fecha_alta", "habilitado", "motivo_inhabilitacion")

    def _a_entidad(self, f):
        return Socio(f["nombre"], f["apellido"], f["documento"], f["email"],
                     f["telefono"], a_fecha(f["fecha_alta"]),
                     bool(f["habilitado"]), f["motivo_inhabilitacion"],
                     id=f["id"])

    def _a_fila(self, s):
        return (s.nombre, s.apellido, s.documento, s.email, s.telefono,
                s.fecha_alta, int(s.habilitado), s.motivo_inhabilitacion)

    def obtener_por_documento(self, documento):
        return self._uno("SELECT * FROM socios WHERE documento = ?",
                         (documento,))

    def listar(self, texto=None, habilitado=None):
        sql, params = "SELECT * FROM socios WHERE 1 = 1", []
        if texto:
            sql += (" AND (nombre LIKE ? OR apellido LIKE ?"
                    " OR documento LIKE ?)")
            params += [f"%{texto}%"] * 3
        if habilitado is not None:
            sql += " AND habilitado = ?"
            params.append(int(habilitado))
        return self._varios(sql + " ORDER BY apellido, nombre", params)


class LibrosSQLite(RepositorioSQLite, RepositorioLibros):
    tabla = "libros"
    columnas = ("isbn", "titulo", "autor", "editorial", "anio_publicacion",
                "genero")

    def _a_entidad(self, f):
        return Libro(f["isbn"], f["titulo"], f["autor"], f["editorial"],
                     f["anio_publicacion"], f["genero"])

    def _a_fila(self, l):
        return (l.isbn, l.titulo, l.autor, l.editorial, l.anio_publicacion,
                l.genero)

    def obtener(self, isbn):
        return self._uno("SELECT * FROM libros WHERE isbn = ?", (isbn,))

    def insertar(self, libro):
        self._cx.execute(
            f"INSERT INTO libros ({', '.join(self.columnas)}) "
            f"VALUES ({marcadores(self.columnas)})", self._a_fila(libro))
        return libro

    def guardar(self, libro):
        self._cx.execute(
            "UPDATE libros SET titulo = ?, autor = ?, editorial = ?, "
            "anio_publicacion = ?, genero = ? WHERE isbn = ?",
            self._a_fila(libro)[1:] + (libro.isbn,))
        return libro

    def listar(self, texto=None):
        if texto:
            patron = f"%{texto}%"
            return self._varios(
                "SELECT * FROM libros WHERE titulo LIKE ? OR autor LIKE ? "
                "OR isbn LIKE ? ORDER BY titulo", (patron, patron, patron))
        return self._varios("SELECT * FROM libros ORDER BY titulo")


class EjemplaresSQLite(RepositorioSQLite, RepositorioEjemplares):
    tabla = "ejemplares"
    columnas = ("isbn", "sede_id", "sede_actual_id", "codigo_inventario",
                "estado", "condicion")

    def _a_entidad(self, f):
        return Ejemplar(f["isbn"], f["sede_id"], f["codigo_inventario"],
                        f["estado"], f["condicion"], f["sede_actual_id"],
                        id=f["id"])

    def _a_fila(self, e):
        return (e.isbn, e.sede_id, e.sede_actual_id, e.codigo_inventario,
                e.estado, e.condicion)

    def obtener_por_codigo(self, codigo_inventario):
        return self._uno(
            "SELECT * FROM ejemplares WHERE codigo_inventario = ?",
            (codigo_inventario.strip().upper(),))

    def listar(self, isbn=None, sede_id=None, estado=None):
        sql, params = "SELECT * FROM ejemplares WHERE 1 = 1", []
        if isbn:
            sql += " AND isbn = ?"
            params.append(isbn)
        if sede_id:
            sql += " AND sede_id = ?"
            params.append(sede_id)
        if estado:
            sql += " AND estado = ?"
            params.append(a_texto(estado))
        return self._varios(sql + " ORDER BY codigo_inventario", params)

    def buscar_disponible(self, isbn, sede_id):
        return self._uno(
            "SELECT * FROM ejemplares WHERE isbn = ? AND sede_id = ? "
            "AND sede_actual_id = sede_id AND estado = ? ORDER BY id LIMIT 1",
            (isbn, sede_id, EstadoEjemplar.DISPONIBLE.value))


class PrestamosSQLite(RepositorioSQLite, RepositorioPrestamos):
    tabla = "prestamos"
    columnas = ("socio_id", "ejemplar_id", "sede_origen_id",
                "sede_destino_id", "tipo", "fecha_solicitud", "dias_prestamo",
                "estado", "fecha_inicio", "fecha_vencimiento",
                "fecha_devolucion", "condicion_devolucion", "multa",
                "observaciones", "reserva_id")

    def _a_entidad(self, f):
        return prestamo_desde_fila(f)

    def _a_fila(self, p):
        return (p.socio_id, p.ejemplar_id, p.sede_origen_id,
                p.sede_destino_id, p.tipo, p.fecha_solicitud,
                p.dias_prestamo, p.estado, p.fecha_inicio,
                p.fecha_vencimiento, p.fecha_devolucion,
                p.condicion_devolucion, p.multa, p.observaciones,
                p.reserva_id)

    def listar(self, estado=None, socio_id=None, sede_id=None):
        sql, params = "SELECT * FROM prestamos WHERE 1 = 1", []
        if estado:
            sql += " AND estado = ?"
            params.append(a_texto(estado))
        if socio_id:
            sql += " AND socio_id = ?"
            params.append(socio_id)
        if sede_id:
            sql += " AND (sede_origen_id = ? OR sede_destino_id = ?)"
            params += [sede_id, sede_id]
        return self._varios(sql + " ORDER BY id DESC", params)

    def abiertos_de_socio(self, socio_id):
        return self._varios(
            f"SELECT * FROM prestamos WHERE socio_id = ? "
            f"AND estado IN ({marcadores(ABIERTOS)})", (socio_id,) + ABIERTOS)

    def abierto_de_ejemplar(self, ejemplar_id):
        return self._uno(
            f"SELECT * FROM prestamos WHERE ejemplar_id = ? "
            f"AND estado IN ({marcadores(ABIERTOS)})",
            (ejemplar_id,) + ABIERTOS)

    def contar_abiertos_de_sede(self, sede_id):
        return self._escalar(
            f"SELECT COUNT(*) FROM prestamos WHERE estado IN "
            f"({marcadores(ABIERTOS)}) AND (sede_origen_id = ? "
            f"OR sede_destino_id = ?)", ABIERTOS + (sede_id, sede_id))


def prestamo_desde_fila(f):
    """Reconstruye un Prestamo (la política de multa se deriva del tipo)."""
    return Prestamo(
        f["socio_id"], f["ejemplar_id"], f["sede_origen_id"],
        f["sede_destino_id"], a_fecha(f["fecha_solicitud"]),
        f["dias_prestamo"], f["estado"],
        fecha_inicio=a_fecha(f["fecha_inicio"]),
        fecha_vencimiento=a_fecha(f["fecha_vencimiento"]),
        fecha_devolucion=a_fecha(f["fecha_devolucion"]),
        condicion_devolucion=f["condicion_devolucion"], multa=f["multa"],
        observaciones=f["observaciones"], reserva_id=f["reserva_id"],
        id=f["id"])


class ReservasSQLite(RepositorioSQLite, RepositorioReservas):
    tabla = "reservas"
    columnas = ("socio_id", "isbn", "sede_id", "fecha_reserva", "estado",
                "ejemplar_id", "fecha_limite_retiro")

    def _a_entidad(self, f):
        return Reserva(f["socio_id"], f["isbn"], f["sede_id"],
                       a_fecha(f["fecha_reserva"]), f["estado"],
                       f["ejemplar_id"], a_fecha(f["fecha_limite_retiro"]),
                       id=f["id"])

    def _a_fila(self, r):
        return (r.socio_id, r.isbn, r.sede_id, r.fecha_reserva, r.estado,
                r.ejemplar_id, r.fecha_limite_retiro)

    def listar(self, estado=None, socio_id=None, sede_id=None):
        sql, params = "SELECT * FROM reservas WHERE 1 = 1", []
        for columna, valor in (("estado", a_texto(estado)),
                               ("socio_id", socio_id), ("sede_id", sede_id)):
            if valor:
                sql += f" AND {columna} = ?"
                params.append(valor)
        return self._varios(sql + " ORDER BY id DESC", params)

    def activa_de_socio(self, socio_id, isbn):
        return self._uno(
            "SELECT * FROM reservas WHERE socio_id = ? AND isbn = ? "
            "AND estado IN (?, ?)",
            (socio_id, isbn, EstadoReserva.PENDIENTE.value,
             EstadoReserva.DISPONIBLE.value))

    def pendientes(self, isbn, sede_id):
        return self._varios(
            "SELECT * FROM reservas WHERE isbn = ? AND sede_id = ? "
            "AND estado = ? ORDER BY fecha_reserva, id",
            (isbn, sede_id, EstadoReserva.PENDIENTE.value))

    def contar_activas_de_sede(self, sede_id):
        return self._escalar(
            "SELECT COUNT(*) FROM reservas WHERE sede_id = ? "
            "AND estado IN (?, ?)",
            (sede_id, EstadoReserva.PENDIENTE.value,
             EstadoReserva.DISPONIBLE.value))


class RemitosSQLite(RepositorioSQLite, RepositorioRemitos):
    """Persiste el remito y su historial (sólo agrega movimientos nuevos)."""

    tabla = "remitos"
    columnas = ("ejemplar_id", "sede_origen_id", "sede_destino_id", "tipo",
                "prestamo_id", "estado", "fecha_creacion")

    def _a_entidad(self, f):
        movimientos = [
            MovimientoRemito(m["estado"], a_fecha_hora(m["fecha_hora"]),
                             m["responsable"], m["ubicacion"],
                             m["observacion"], m["tipo_incidencia"],
                             m["condicion"])
            for m in self._cx.execute(
                "SELECT * FROM movimientos_remito WHERE remito_id = ? "
                "ORDER BY orden", (f["id"],))
        ]
        return Remito(f["ejemplar_id"], f["sede_origen_id"],
                      f["sede_destino_id"], f["tipo"],
                      a_fecha_hora(f["fecha_creacion"]), f["prestamo_id"],
                      estado=f["estado"], historial=movimientos, id=f["id"])

    def _a_fila(self, r):
        return (r.ejemplar_id, r.sede_origen_id, r.sede_destino_id, r.tipo,
                r.prestamo_id, r.estado, r.fecha_creacion)

    def guardar(self, remito):
        super().guardar(remito)
        persistidos = self._escalar(
            "SELECT COUNT(*) FROM movimientos_remito WHERE remito_id = ?",
            (remito.id,))
        for orden, m in enumerate(remito.historial):
            if orden < persistidos:
                continue
            self._cx.execute(
                "INSERT INTO movimientos_remito (remito_id, orden, estado, "
                "fecha_hora, responsable, ubicacion, observacion, "
                "tipo_incidencia, condicion) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)",
                (remito.id, orden, m.estado, a_texto(m.fecha_hora),
                 m.responsable, m.ubicacion, m.observacion,
                 m.tipo_incidencia, m.condicion))
        return remito

    def listar(self, estado=None, sede_id=None, tipo=None):
        sql, params = "SELECT * FROM remitos WHERE 1 = 1", []
        if estado:
            sql += " AND estado = ?"
            params.append(a_texto(estado))
        if tipo:
            sql += " AND tipo = ?"
            params.append(a_texto(tipo))
        if sede_id:
            sql += " AND (sede_origen_id = ? OR sede_destino_id = ?)"
            params += [sede_id, sede_id]
        return self._varios(sql + " ORDER BY id DESC", params)

    def en_curso_de_ejemplar(self, ejemplar_id):
        return self._uno(
            f"SELECT * FROM remitos WHERE ejemplar_id = ? AND estado IN "
            f"({marcadores(ESTADOS_EN_CURSO)})",
            (ejemplar_id,) + ESTADOS_EN_CURSO)

    def de_prestamo(self, prestamo_id):
        return self._varios(
            "SELECT * FROM remitos WHERE prestamo_id = ? ORDER BY id",
            (prestamo_id,))

    def contar_en_curso_de_sede(self, sede_id):
        return self._escalar(
            f"SELECT COUNT(*) FROM remitos WHERE estado IN "
            f"({marcadores(ESTADOS_EN_CURSO)}) AND (sede_origen_id = ? "
            f"OR sede_destino_id = ?)", ESTADOS_EN_CURSO + (sede_id, sede_id))


class NotificacionesSQLite(RepositorioSQLite, RepositorioNotificaciones):
    tabla = "notificaciones"
    columnas = ("socio_id", "mensaje", "fecha_hora", "leida")

    def _a_entidad(self, f):
        return Notificacion(f["socio_id"], f["mensaje"],
                            a_fecha_hora(f["fecha_hora"]), bool(f["leida"]),
                            id=f["id"])

    def _a_fila(self, n):
        return (n.socio_id, n.mensaje, n.fecha_hora, int(n.leida))

    def listar(self, socio_id, solo_no_leidas=False):
        filtro = " AND leida = 0" if solo_no_leidas else ""
        return self._varios(
            f"SELECT * FROM notificaciones WHERE socio_id = ?{filtro} "
            f"ORDER BY fecha_hora DESC, id DESC", (socio_id,))


class UnidadDeTrabajoSQLite(UnidadDeTrabajo):
    """Una conexión = una transacción compartida por todos los repositorios."""

    def __init__(self, ruta_db):
        self.conexion = conectar(ruta_db)
        self.sedes = SedesSQLite(self.conexion)
        self.socios = SociosSQLite(self.conexion)
        self.libros = LibrosSQLite(self.conexion)
        self.ejemplares = EjemplaresSQLite(self.conexion)
        self.prestamos = PrestamosSQLite(self.conexion)
        self.reservas = ReservasSQLite(self.conexion)
        self.remitos = RemitosSQLite(self.conexion)
        self.notificaciones = NotificacionesSQLite(self.conexion)

    def confirmar(self):
        self.conexion.commit()

    def revertir(self):
        self.conexion.rollback()

    def cerrar(self):
        self.conexion.close()
