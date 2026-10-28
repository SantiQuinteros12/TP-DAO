"""Caso de uso: recomendaciones de lectura para socios y por libro."""

from collections import defaultdict
from datetime import timedelta

from domain.excepciones import EntidadNoEncontradaError
from domain.recomendacion import ContextoRecomendacion, MotorRecomendacion

DIAS_TENDENCIA = 90


class RecomendacionService:
    """
    :param consultas: consultas de lectura (ConsultasSQLite)
    :param uow: unidad de trabajo (para validar socio y libro)
    :param reloj: fuente de fecha/hora
    """

    def __init__(self, consultas, uow, reloj):
        self.consultas = consultas
        self.uow = uow
        self.reloj = reloj

    def _datos(self):
        desde = self.reloj.hoy() - timedelta(days=DIAS_TENDENCIA)
        libros = {l["isbn"]: l for l in
                  self.consultas.libros_para_recomendar(desde)}
        lectores = defaultdict(set)
        for fila in self.consultas.historial_lectura():
            lectores[fila["isbn"]].add(fila["socio_id"])
        return libros, lectores

    def para_socio(self, socio_id=None, limite=8):
        """
        Recomendaciones personalizadas según el historial del socio. Sin
        socio, o si todavía no pidió libros, devuelve las tendencias.
        """
        libros, lectores = self._datos()
        socio = None
        leidos = set()
        if socio_id:
            socio = self.uow.socios.obtener(socio_id)
            if socio is None:
                raise EntidadNoEncontradaError(
                    f"Socio con id {socio_id} no encontrado")
            leidos = {i for i, socios in lectores.items()
                      if socio_id in socios}
        ctx = ContextoRecomendacion(libros, lectores, leidos, socio_id)
        motor = (MotorRecomendacion.personalizado() if ctx.tiene_historial
                 else MotorRecomendacion.por_tendencia())
        return {
            "socio": socio.nombre_completo if socio else None,
            "personalizado": ctx.tiene_historial,
            "perfil": {
                "libros_leidos": [libros[i]["titulo"] for i in sorted(leidos)
                                  if i in libros],
                "generos": [{"genero": g, "cantidad": n}
                            for g, n in ctx.generos.most_common()],
                "autores": [{"autor": a, "cantidad": n}
                            for a, n in ctx.autores.most_common(5)],
            },
            "recomendaciones": [self._serializar(r)
                                for r in motor.recomendar(ctx, limite)],
        }

    def similares(self, isbn, limite=6):
        """"Quienes leyeron este libro también leyeron…" + mismo género/autor."""
        libros, lectores = self._datos()
        if isbn not in libros:
            raise EntidadNoEncontradaError(f"Libro con ISBN {isbn} no encontrado")
        ctx = ContextoRecomendacion(libros, lectores, {isbn})
        return {
            "libro": libros[isbn],
            "recomendaciones": [
                self._serializar(r) for r in
                MotorRecomendacion.personalizado().recomendar(ctx, limite)],
        }

    @staticmethod
    def _serializar(r):
        sedes = r.libro["sedes_disponibles"]
        return {**r.libro, "puntaje": r.puntaje, "motivos": r.motivos,
                "sedes_disponibles": sedes.split(",") if sedes else []}
