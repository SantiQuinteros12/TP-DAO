"""
Consultas de sólo lectura (listados enriquecidos y reportes).

Separar lecturas de escrituras (CQRS liviano) evita cargar agregados
completos sólo para mostrar una grilla: aquí se usan JOINs y agregaciones
SQL, mientras que las modificaciones pasan siempre por entidades y
repositorios.
"""

from domain.remito import ESTADOS_EN_CURSO
from infrastructure.repositorios_sqlite import (a_fecha_hora, marcadores,
                                                prestamo_desde_fila)

EN_VIAJE = ("DESPACHADO", "EN_TRANSITO", "CON_INCIDENCIA")


def _dicts(cursor):
    return [dict(f) for f in cursor.fetchall()]


class ConsultasSQLite:

    def __init__(self, conexion):
        self._cx = conexion

    # ===================================================================
    # Listados
    # ===================================================================
    def ejemplares(self, isbn=None, sede_id=None, estado=None, texto=None):
        sql = """
            SELECT e.*, l.titulo, l.autor,
                   sp.nombre AS sede, sa.nombre AS sede_actual
              FROM ejemplares e
              JOIN libros l ON l.isbn = e.isbn
              JOIN sedes sp ON sp.id = e.sede_id
              JOIN sedes sa ON sa.id = e.sede_actual_id
             WHERE 1 = 1"""
        params = []
        if isbn:
            sql += " AND e.isbn = ?"
            params.append(isbn)
        if sede_id:
            sql += " AND e.sede_id = ?"
            params.append(sede_id)
        if estado:
            sql += " AND e.estado = ?"
            params.append(estado)
        if texto:
            sql += (" AND (l.titulo LIKE ? OR l.autor LIKE ?"
                    " OR e.codigo_inventario LIKE ?)")
            params += [f"%{texto}%"] * 3
        return _dicts(self._cx.execute(
            sql + " ORDER BY l.titulo, e.codigo_inventario", params))

    def disponibilidad(self, isbn=None, sede_id=None, texto=None):
        """Matriz libro x sede con el conteo de ejemplares por estado."""
        sql = """
            SELECT l.isbn, l.titulo, l.autor,
                   s.id AS sede_id, s.nombre AS sede, s.activa AS sede_activa,
                   COUNT(e.id) AS total,
                   SUM(e.estado = 'DISPONIBLE'
                       AND e.sede_actual_id = e.sede_id) AS disponibles,
                   SUM(e.estado = 'RESERVADO')   AS reservados,
                   SUM(e.estado = 'EN_PRESTAMO') AS prestados,
                   SUM(e.estado = 'EN_TRANSITO') AS en_transito,
                   SUM(e.estado = 'DANADO')      AS danados,
                   (SELECT COUNT(*) FROM reservas r
                     WHERE r.isbn = l.isbn AND r.sede_id = s.id
                       AND r.estado = 'PENDIENTE') AS reservas_en_espera
              FROM ejemplares e
              JOIN libros l ON l.isbn = e.isbn
              JOIN sedes s ON s.id = e.sede_id
             WHERE e.estado <> 'BAJA'"""
        params = []
        if isbn:
            sql += " AND l.isbn = ?"
            params.append(isbn)
        if sede_id:
            sql += " AND s.id = ?"
            params.append(sede_id)
        if texto:
            sql += " AND (l.titulo LIKE ? OR l.autor LIKE ? OR l.isbn LIKE ?)"
            params += [f"%{texto}%"] * 3
        return _dicts(self._cx.execute(
            sql + " GROUP BY l.isbn, s.id ORDER BY l.titulo, s.nombre",
            params))

    def prestamos(self, hoy, estado=None, socio_id=None, sede_id=None,
                  tipo=None, solo_vencidos=False):
        sql = """
            SELECT p.*, so.apellido || ', ' || so.nombre AS socio,
                   so.documento, e.codigo_inventario, l.titulo, l.isbn,
                   s1.nombre AS sede_origen, s2.nombre AS sede_destino
              FROM prestamos p
              JOIN socios so ON so.id = p.socio_id
              JOIN ejemplares e ON e.id = p.ejemplar_id
              JOIN libros l ON l.isbn = e.isbn
              JOIN sedes s1 ON s1.id = p.sede_origen_id
              JOIN sedes s2 ON s2.id = p.sede_destino_id
             WHERE 1 = 1"""
        params = []
        if estado:
            sql += " AND p.estado = ?"
            params.append(estado)
        if socio_id:
            sql += " AND p.socio_id = ?"
            params.append(socio_id)
        if sede_id:
            sql += " AND (p.sede_origen_id = ? OR p.sede_destino_id = ?)"
            params += [sede_id, sede_id]
        if tipo:
            sql += " AND p.tipo = ?"
            params.append(tipo)
        if solo_vencidos:
            sql += " AND p.estado = 'ACTIVO' AND p.fecha_vencimiento < ?"
            params.append(hoy.isoformat())
        filas = self._cx.execute(sql + " ORDER BY p.id DESC", params)
        resultado = []
        for fila in filas:
            prestamo = prestamo_desde_fila(fila)
            datos = dict(fila)
            datos.update(
                vencido=prestamo.esta_vencido(hoy),
                dias_atraso=prestamo.dias_atraso(hoy),
                multa_estimada=prestamo.multa_estimada(hoy),
                politica_multa=prestamo.politica_multa.nombre)
            resultado.append(datos)
        return resultado

    def reservas(self, estado=None, socio_id=None, sede_id=None):
        sql = """
            SELECT r.*, so.apellido || ', ' || so.nombre AS socio,
                   l.titulo, s.nombre AS sede, e.codigo_inventario
              FROM reservas r
              JOIN socios so ON so.id = r.socio_id
              JOIN libros l ON l.isbn = r.isbn
              JOIN sedes s ON s.id = r.sede_id
              LEFT JOIN ejemplares e ON e.id = r.ejemplar_id
             WHERE 1 = 1"""
        params = []
        for columna, valor in (("r.estado", estado), ("r.socio_id", socio_id),
                               ("r.sede_id", sede_id)):
            if valor:
                sql += f" AND {columna} = ?"
                params.append(valor)
        return _dicts(self._cx.execute(sql + " ORDER BY r.id DESC", params))

    def remitos(self, estado=None, sede_id=None, tipo=None, en_curso=False):
        sql = """
            SELECT r.*, e.codigo_inventario, l.titulo,
                   s1.nombre AS sede_origen, s2.nombre AS sede_destino,
                   (SELECT MAX(m.fecha_hora) FROM movimientos_remito m
                     WHERE m.remito_id = r.id) AS ultima_actualizacion,
                   (SELECT COUNT(*) FROM movimientos_remito m
                     WHERE m.remito_id = r.id
                       AND m.tipo_incidencia IS NOT NULL) AS incidencias
              FROM remitos r
              JOIN ejemplares e ON e.id = r.ejemplar_id
              JOIN libros l ON l.isbn = e.isbn
              JOIN sedes s1 ON s1.id = r.sede_origen_id
              JOIN sedes s2 ON s2.id = r.sede_destino_id
             WHERE 1 = 1"""
        params = []
        if estado:
            sql += " AND r.estado = ?"
            params.append(estado)
        if tipo:
            sql += " AND r.tipo = ?"
            params.append(tipo)
        if sede_id:
            sql += " AND (r.sede_origen_id = ? OR r.sede_destino_id = ?)"
            params += [sede_id, sede_id]
        if en_curso:
            sql += f" AND r.estado IN ({marcadores(ESTADOS_EN_CURSO)})"
            params += list(ESTADOS_EN_CURSO)
        return _dicts(self._cx.execute(sql + " ORDER BY r.id DESC", params))

    # ===================================================================
    # Reportes
    # ===================================================================
    def resumen_operativo_por_sede(self):
        """Reporte 1: préstamos activos y material en tránsito por sede."""
        en_viaje = marcadores(EN_VIAJE)
        return _dicts(self._cx.execute(f"""
            SELECT s.id AS sede_id, s.nombre AS sede, s.activa,
              (SELECT COUNT(*) FROM prestamos p WHERE p.estado = 'ACTIVO'
                  AND p.sede_destino_id = s.id AND p.tipo = 'LOCAL')
                  AS activos_locales,
              (SELECT COUNT(*) FROM prestamos p WHERE p.estado = 'ACTIVO'
                  AND p.sede_destino_id = s.id
                  AND p.tipo = 'INTERBIBLIOTECARIO') AS activos_interbib,
              (SELECT COUNT(*) FROM prestamos p
                WHERE p.estado IN ('PENDIENTE_ENVIO', 'LISTO_PARA_RETIRO')
                  AND p.sede_destino_id = s.id) AS pendientes_de_entrega,
              (SELECT COUNT(*) FROM remitos r
                WHERE r.estado IN ('CREADO', 'EMPAQUETADO')
                  AND r.sede_origen_id = s.id) AS por_despachar,
              (SELECT COUNT(*) FROM remitos r WHERE r.estado IN ({en_viaje})
                  AND r.sede_origen_id = s.id) AS salientes_en_transito,
              (SELECT COUNT(*) FROM remitos r WHERE r.estado IN ({en_viaje})
                  AND r.sede_destino_id = s.id) AS entrantes_en_transito
              FROM sedes s ORDER BY s.nombre""", EN_VIAJE * 2))

    def material_en_transito(self, ahora):
        filas = _dicts(self._cx.execute(f"""
            SELECT r.id, r.tipo, r.estado, e.codigo_inventario, l.titulo,
                   s1.nombre AS sede_origen, s2.nombre AS sede_destino,
                   (SELECT MIN(m.fecha_hora) FROM movimientos_remito m
                     WHERE m.remito_id = r.id AND m.estado = 'DESPACHADO')
                     AS despachado_en
              FROM remitos r
              JOIN ejemplares e ON e.id = r.ejemplar_id
              JOIN libros l ON l.isbn = e.isbn
              JOIN sedes s1 ON s1.id = r.sede_origen_id
              JOIN sedes s2 ON s2.id = r.sede_destino_id
             WHERE r.estado IN ({marcadores(EN_VIAJE)})
             ORDER BY despachado_en""", EN_VIAJE))
        for fila in filas:
            despacho = a_fecha_hora(fila["despachado_en"])
            fila["horas_en_transito"] = (
                round((ahora - despacho).total_seconds() / 3600, 1)
                if despacho else None)
        return filas

    def multas_registradas_por_socio(self, limite=10):
        return _dicts(self._cx.execute("""
            SELECT so.id AS socio_id, so.apellido || ', ' || so.nombre AS socio,
                   COUNT(*) AS prestamos_con_multa,
                   ROUND(SUM(p.multa), 2) AS total_multas
              FROM prestamos p JOIN socios so ON so.id = p.socio_id
             WHERE p.estado = 'DEVUELTO' AND p.multa > 0
             GROUP BY so.id ORDER BY total_multas DESC LIMIT ?""", (limite,)))

    def libros_mas_solicitados_intersede(self, desde, hasta, limite=10):
        """Reporte 3: ranking de libros pedidos entre sedes."""
        return _dicts(self._cx.execute("""
            SELECT l.isbn, l.titulo, l.autor,
                   COUNT(*) AS solicitudes,
                   COUNT(DISTINCT p.sede_destino_id) AS sedes_solicitantes,
                   COUNT(DISTINCT p.sede_origen_id)  AS sedes_proveedoras,
                   SUM(p.estado = 'CANCELADO') AS canceladas,
                   GROUP_CONCAT(DISTINCT s.nombre) AS solicitado_desde
              FROM prestamos p
              JOIN ejemplares e ON e.id = p.ejemplar_id
              JOIN libros l ON l.isbn = e.isbn
              JOIN sedes s ON s.id = p.sede_destino_id
             WHERE p.tipo = 'INTERBIBLIOTECARIO'
               AND p.fecha_solicitud BETWEEN ? AND ?
             GROUP BY l.isbn
             ORDER BY solicitudes DESC, l.titulo
             LIMIT ?""", (desde.isoformat(), hasta.isoformat(), limite)))

    def disponibilidad_por_sede(self):
        """Reporte 4: disponibilidad del catálogo agregada por sede."""
        filas = _dicts(self._cx.execute("""
            SELECT s.id AS sede_id, s.nombre AS sede, s.activa,
                   COUNT(e.id) AS total_ejemplares,
                   COUNT(DISTINCT e.isbn) AS titulos,
                   COALESCE(SUM(e.estado = 'DISPONIBLE'
                                AND e.sede_actual_id = e.sede_id), 0)
                       AS disponibles,
                   COALESCE(SUM(e.estado = 'EN_PRESTAMO'), 0) AS prestados,
                   COALESCE(SUM(e.estado = 'RESERVADO'), 0)   AS reservados,
                   COALESCE(SUM(e.estado = 'EN_TRANSITO'), 0) AS en_transito,
                   COALESCE(SUM(e.estado = 'DANADO'), 0)      AS danados,
                   COALESCE(SUM(e.sede_actual_id <> e.sede_id), 0)
                       AS fuera_de_sede
              FROM sedes s
              LEFT JOIN ejemplares e
                     ON e.sede_id = s.id AND e.estado <> 'BAJA'
             GROUP BY s.id ORDER BY s.nombre"""))
        for fila in filas:
            total = fila["total_ejemplares"]
            fila["porcentaje_disponible"] = (
                round(100 * fila["disponibles"] / total, 1) if total else 0.0)
        return filas

    def remitos_con_tiempos(self, desde, hasta):
        """Base del reporte 5: un registro por remito con sus hitos."""
        return _dicts(self._cx.execute("""
            SELECT r.id, r.tipo, r.estado, r.sede_origen_id, r.sede_destino_id,
                   s1.nombre AS sede_origen, s2.nombre AS sede_destino,
                   (SELECT MIN(m.fecha_hora) FROM movimientos_remito m
                     WHERE m.remito_id = r.id AND m.estado = 'DESPACHADO')
                     AS despachado_en,
                   (SELECT MAX(m.fecha_hora) FROM movimientos_remito m
                     WHERE m.remito_id = r.id AND m.estado = 'RECIBIDO')
                     AS recibido_en,
                   (SELECT COUNT(*) FROM movimientos_remito m
                     WHERE m.remito_id = r.id
                       AND m.tipo_incidencia IS NOT NULL) AS incidencias
              FROM remitos r
              JOIN sedes s1 ON s1.id = r.sede_origen_id
              JOIN sedes s2 ON s2.id = r.sede_destino_id
             WHERE substr(r.fecha_creacion, 1, 10) BETWEEN ? AND ?""",
            (desde.isoformat(), hasta.isoformat())))

    def incidencias_por_tipo(self, desde, hasta):
        return _dicts(self._cx.execute("""
            SELECT m.tipo_incidencia AS tipo, COUNT(*) AS cantidad
              FROM movimientos_remito m JOIN remitos r ON r.id = m.remito_id
             WHERE m.tipo_incidencia IS NOT NULL
               AND substr(r.fecha_creacion, 1, 10) BETWEEN ? AND ?
             GROUP BY m.tipo_incidencia ORDER BY cantidad DESC""",
            (desde.isoformat(), hasta.isoformat())))

    def totales(self):
        fila = self._cx.execute("""
            SELECT (SELECT COUNT(*) FROM sedes WHERE activa = 1) AS sedes_activas,
                   (SELECT COUNT(*) FROM socios WHERE habilitado = 1)
                       AS socios_habilitados,
                   (SELECT COUNT(*) FROM libros) AS titulos,
                   (SELECT COUNT(*) FROM ejemplares WHERE estado <> 'BAJA')
                       AS ejemplares,
                   (SELECT COUNT(*) FROM prestamos WHERE estado = 'ACTIVO')
                       AS prestamos_activos,
                   (SELECT COUNT(*) FROM reservas
                     WHERE estado IN ('PENDIENTE', 'DISPONIBLE'))
                       AS reservas_activas""").fetchone()
        return dict(fila)
