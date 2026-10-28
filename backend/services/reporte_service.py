"""Reportes de gestión (no triviales) sobre la operación de la red."""

from collections import defaultdict
from datetime import timedelta

from infrastructure.repositorios_sqlite import a_fecha_hora


def _horas(desde, hasta):
    return (a_fecha_hora(hasta) - a_fecha_hora(desde)).total_seconds() / 3600


def _promedio(valores):
    return round(sum(valores) / len(valores), 1) if valores else None


class ReporteService:
    """
    :param consultas: objeto de consultas de lectura (ConsultasSQLite)
    :param reloj: fuente de fecha/hora
    """

    def __init__(self, consultas, reloj):
        self.consultas = consultas
        self.reloj = reloj

    def _rango(self, desde, hasta, dias_por_defecto=365):
        hasta = hasta or self.reloj.hoy()
        desde = desde or hasta - timedelta(days=dias_por_defecto)
        return desde, hasta

    def resumen(self):
        return self.consultas.totales()

    def prestamos_activos_y_transito(self):
        """
        Reporte 1: por sede, préstamos activos (locales/interbibliotecarios),
        pendientes de entrega y remitos salientes/entrantes en viaje, más el
        detalle del material en tránsito con su antigüedad.
        """
        por_sede = self.consultas.resumen_operativo_por_sede()
        en_transito = self.consultas.material_en_transito(self.reloj.ahora())
        claves = ("activos_locales", "activos_interbib",
                  "pendientes_de_entrega", "por_despachar",
                  "salientes_en_transito")
        return {
            "por_sede": por_sede,
            "en_transito": en_transito,
            "totales": {c: sum(f[c] for f in por_sede) for c in claves},
        }

    def vencidos_y_multas(self):
        """
        Reporte 2: préstamos vencidos con días de atraso y multa estimada
        (según la política de cada tipo), agregados por sede, y ranking de
        multas ya registradas en devoluciones.
        """
        hoy = self.reloj.hoy()
        vencidos = self.consultas.prestamos(hoy, solo_vencidos=True)
        por_sede = defaultdict(lambda: {"cantidad": 0, "multa_estimada": 0.0,
                                        "max_dias_atraso": 0})
        for p in vencidos:
            acumulado = por_sede[p["sede_destino"]]
            acumulado["cantidad"] += 1
            acumulado["multa_estimada"] += p["multa_estimada"]
            acumulado["max_dias_atraso"] = max(acumulado["max_dias_atraso"],
                                               p["dias_atraso"])
        return {
            "fecha_corte": hoy.isoformat(),
            "detalle": sorted(vencidos, key=lambda p: -p["dias_atraso"]),
            "por_sede": [{"sede": s, **{k: round(v, 2) if isinstance(v, float)
                                        else v for k, v in d.items()}}
                         for s, d in sorted(por_sede.items())],
            "total_estimado": round(sum(p["multa_estimada"]
                                        for p in vencidos), 2),
            "multas_registradas": self.consultas.multas_registradas_por_socio(),
        }

    def libros_mas_solicitados(self, desde=None, hasta=None, limite=10):
        """Reporte 3: libros más pedidos en préstamos inter-sedes."""
        desde, hasta = self._rango(desde, hasta)
        return {
            "desde": desde.isoformat(), "hasta": hasta.isoformat(),
            "ranking": self.consultas.libros_mas_solicitados_intersede(
                desde, hasta, limite),
        }

    def disponibilidad_por_sede(self):
        """Reporte 4: disponibilidad del catálogo por sede."""
        return self.consultas.disponibilidad_por_sede()

    def logistica(self, desde=None, hasta=None):
        """
        Reporte 5: tasa de envíos exitosos e incidencias, movimiento de
        ejemplares por ruta origen/destino y tiempo promedio de tránsito
        (desde el despacho hasta la recepción).
        """
        desde, hasta = self._rango(desde, hasta)
        remitos = self.consultas.remitos_con_tiempos(desde, hasta)

        recibidos = [r for r in remitos if r["estado"] == "RECIBIDO"]
        extraviados = [r for r in remitos if r["estado"] == "EXTRAVIADO"]
        finalizados = len(recibidos) + len(extraviados)
        exitosos = [r for r in recibidos if r["incidencias"] == 0]
        despachados = [r for r in remitos if r["despachado_en"]]
        con_incidencia = [r for r in despachados if r["incidencias"] > 0]
        tiempos = [_horas(r["despachado_en"], r["recibido_en"])
                   for r in recibidos if r["despachado_en"]]

        rutas = defaultdict(lambda: {"envios": 0, "recibidos": 0,
                                     "incidencias": 0, "_tiempos": []})
        por_sede = defaultdict(lambda: {"enviados": 0, "recibidos": 0})
        for r in remitos:
            ruta = rutas[(r["sede_origen"], r["sede_destino"])]
            ruta["envios"] += 1
            ruta["incidencias"] += 1 if r["incidencias"] else 0
            por_sede[r["sede_origen"]]["enviados"] += 1
            if r["estado"] == "RECIBIDO":
                ruta["recibidos"] += 1
                por_sede[r["sede_destino"]]["recibidos"] += 1
                if r["despachado_en"]:
                    ruta["_tiempos"].append(
                        _horas(r["despachado_en"], r["recibido_en"]))

        def porcentaje(parte, total):
            return round(100 * parte / total, 1) if total else None

        return {
            "desde": desde.isoformat(), "hasta": hasta.isoformat(),
            "indicadores": {
                "remitos_emitidos": len(remitos),
                "despachados": len(despachados),
                "recibidos": len(recibidos),
                "recibidos_sin_incidencias": len(exitosos),
                "extraviados": len(extraviados),
                "cancelados": sum(r["estado"] == "CANCELADO" for r in remitos),
                "en_curso": sum(r["estado"] not in (
                    "RECIBIDO", "EXTRAVIADO", "CANCELADO") for r in remitos),
                "tasa_exito": porcentaje(len(exitosos), finalizados),
                "tasa_incidencias": porcentaje(len(con_incidencia),
                                               len(despachados)),
                "horas_promedio_transito": _promedio(tiempos),
            },
            "incidencias_por_tipo": self.consultas.incidencias_por_tipo(
                desde, hasta),
            "rutas": sorted(
                ({"sede_origen": o, "sede_destino": d,
                  "envios": v["envios"], "recibidos": v["recibidos"],
                  "con_incidencias": v["incidencias"],
                  "horas_promedio": _promedio(v["_tiempos"]),
                  "horas_min": round(min(v["_tiempos"]), 1)
                  if v["_tiempos"] else None,
                  "horas_max": round(max(v["_tiempos"]), 1)
                  if v["_tiempos"] else None}
                 for (o, d), v in rutas.items()),
                key=lambda x: -x["envios"]),
            "por_sede": [{"sede": s, **v}
                         for s, v in sorted(por_sede.items())],
        }
