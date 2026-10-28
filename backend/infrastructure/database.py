"""Conexión y esquema de la base de datos SQLite."""

import sqlite3

ESQUEMA = """
CREATE TABLE IF NOT EXISTS sedes (
    id          INTEGER PRIMARY KEY AUTOINCREMENT,
    nombre      TEXT    NOT NULL UNIQUE COLLATE NOCASE,
    direccion      TEXT    NOT NULL,          -- texto completo (lectura)
    calle          TEXT    NOT NULL DEFAULT '',
    numero         TEXT    NOT NULL DEFAULT '',
    piso_depto     TEXT    DEFAULT '',
    barrio         TEXT    DEFAULT '',
    ciudad         TEXT    NOT NULL DEFAULT '',
    provincia      TEXT    NOT NULL DEFAULT '',
    codigo_postal  TEXT    DEFAULT '',
    telefono       TEXT    DEFAULT '',
    email          TEXT    DEFAULT '',
    horario        TEXT    DEFAULT '[]',      -- JSON: franjas horarias
    activa         INTEGER NOT NULL DEFAULT 1
);

CREATE TABLE IF NOT EXISTS socios (
    id                     INTEGER PRIMARY KEY AUTOINCREMENT,
    nombre                 TEXT NOT NULL,
    apellido               TEXT NOT NULL,
    documento              TEXT NOT NULL UNIQUE,
    email                  TEXT DEFAULT '',
    telefono               TEXT DEFAULT '',
    fecha_alta             TEXT NOT NULL,
    habilitado             INTEGER NOT NULL DEFAULT 1,
    motivo_inhabilitacion  TEXT
);

CREATE TABLE IF NOT EXISTS libros (
    isbn              TEXT PRIMARY KEY,
    titulo            TEXT NOT NULL,
    autor             TEXT NOT NULL,
    editorial         TEXT DEFAULT '',
    anio_publicacion  INTEGER,
    genero            TEXT DEFAULT ''
);

CREATE TABLE IF NOT EXISTS ejemplares (
    id                 INTEGER PRIMARY KEY AUTOINCREMENT,
    isbn               TEXT    NOT NULL REFERENCES libros(isbn),
    sede_id            INTEGER NOT NULL REFERENCES sedes(id),
    sede_actual_id     INTEGER NOT NULL REFERENCES sedes(id),
    codigo_inventario  TEXT    NOT NULL UNIQUE,
    estado             TEXT    NOT NULL,
    condicion          TEXT    NOT NULL
);

CREATE TABLE IF NOT EXISTS reservas (
    id                   INTEGER PRIMARY KEY AUTOINCREMENT,
    socio_id             INTEGER NOT NULL REFERENCES socios(id),
    isbn                 TEXT    NOT NULL REFERENCES libros(isbn),
    sede_id              INTEGER NOT NULL REFERENCES sedes(id),
    fecha_reserva        TEXT    NOT NULL,
    estado               TEXT    NOT NULL,
    ejemplar_id          INTEGER REFERENCES ejemplares(id),
    fecha_limite_retiro  TEXT
);

CREATE TABLE IF NOT EXISTS prestamos (
    id                    INTEGER PRIMARY KEY AUTOINCREMENT,
    socio_id              INTEGER NOT NULL REFERENCES socios(id),
    ejemplar_id           INTEGER NOT NULL REFERENCES ejemplares(id),
    sede_origen_id        INTEGER NOT NULL REFERENCES sedes(id),
    sede_destino_id       INTEGER NOT NULL REFERENCES sedes(id),
    tipo                  TEXT    NOT NULL,
    fecha_solicitud       TEXT    NOT NULL,
    dias_prestamo         INTEGER NOT NULL,
    estado                TEXT    NOT NULL,
    fecha_inicio          TEXT,
    fecha_vencimiento     TEXT,
    fecha_devolucion      TEXT,
    condicion_devolucion  TEXT,
    multa                 REAL    NOT NULL DEFAULT 0,
    observaciones         TEXT    DEFAULT '',
    reserva_id            INTEGER REFERENCES reservas(id)
);

CREATE TABLE IF NOT EXISTS remitos (
    id               INTEGER PRIMARY KEY AUTOINCREMENT,
    ejemplar_id      INTEGER NOT NULL REFERENCES ejemplares(id),
    sede_origen_id   INTEGER NOT NULL REFERENCES sedes(id),
    sede_destino_id  INTEGER NOT NULL REFERENCES sedes(id),
    tipo             TEXT    NOT NULL,
    prestamo_id      INTEGER REFERENCES prestamos(id),
    estado           TEXT    NOT NULL,
    fecha_creacion   TEXT    NOT NULL
);

-- Historial append-only: base de la trazabilidad del remito.
CREATE TABLE IF NOT EXISTS movimientos_remito (
    id               INTEGER PRIMARY KEY AUTOINCREMENT,
    remito_id        INTEGER NOT NULL REFERENCES remitos(id),
    orden            INTEGER NOT NULL,
    estado           TEXT    NOT NULL,
    fecha_hora       TEXT    NOT NULL,
    responsable      TEXT    DEFAULT '',
    ubicacion        TEXT    DEFAULT '',
    observacion      TEXT    DEFAULT '',
    tipo_incidencia  TEXT,
    condicion        TEXT,
    UNIQUE (remito_id, orden)
);

CREATE TABLE IF NOT EXISTS notificaciones (
    id          INTEGER PRIMARY KEY AUTOINCREMENT,
    socio_id    INTEGER NOT NULL REFERENCES socios(id),
    mensaje     TEXT    NOT NULL,
    fecha_hora  TEXT    NOT NULL,
    leida       INTEGER NOT NULL DEFAULT 0
);

CREATE INDEX IF NOT EXISTS ix_ejemplares_isbn_sede
    ON ejemplares (isbn, sede_actual_id, estado);
CREATE INDEX IF NOT EXISTS ix_prestamos_estado ON prestamos (estado);
CREATE INDEX IF NOT EXISTS ix_remitos_estado ON remitos (estado);
CREATE INDEX IF NOT EXISTS ix_movimientos_remito ON movimientos_remito (remito_id);
"""


def conectar(ruta_db):
    """
    Abre una conexión con claves foráneas activas y filas tipo diccionario.

    ``check_same_thread=False`` porque FastAPI puede ejecutar la dependencia
    y el endpoint en hilos distintos del pool; cada request usa su propia
    conexión, así que no se comparte entre requests concurrentes.
    """
    conexion = sqlite3.connect(ruta_db, check_same_thread=False)
    conexion.row_factory = sqlite3.Row
    conexion.execute("PRAGMA foreign_keys = ON")
    return conexion


# Columnas agregadas a ``sedes`` al estructurar la dirección.
_COLUMNAS_DIRECCION = ("calle", "numero", "piso_depto", "barrio", "ciudad",
                       "provincia", "codigo_postal")


def _migrar(conexion):
    """Adapta bases creadas con versiones anteriores del esquema."""
    existentes = {f["name"] for f in
                  conexion.execute("PRAGMA table_info(sedes)")}
    faltantes = [c for c in _COLUMNAS_DIRECCION if c not in existentes]
    for columna in faltantes:
        conexion.execute(
            f"ALTER TABLE sedes ADD COLUMN {columna} TEXT NOT NULL DEFAULT ''")
    if faltantes:
        # La dirección vieja era texto libre: se conserva como calle.
        conexion.execute("""
            UPDATE sedes SET calle = direccion, numero = 'S/N',
                   ciudad = 'Córdoba', provincia = 'Córdoba'
             WHERE calle = ''""")
        conexion.execute(
            "UPDATE sedes SET horario = '[]' WHERE horario NOT LIKE '[%'")


def inicializar_esquema(ruta_db):
    conexion = conectar(ruta_db)
    try:
        conexion.executescript(ESQUEMA)
        _migrar(conexion)
        conexion.commit()
    finally:
        conexion.close()
