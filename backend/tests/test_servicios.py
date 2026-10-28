"""Tests de integración de los casos de uso contra SQLite."""

import pytest

from domain.enums import (EstadoEjemplar, EstadoPrestamo, EstadoReserva,
                          TipoPrestamo)
from domain.excepciones import (DuplicadoError, ReglaNegocioError,
                                TransicionInvalidaError)
from infrastructure.consultas_sqlite import ConsultasSQLite
from services.reporte_service import ReporteService
from tests.conftest import ISBN_FICCIONES, ISBN_RAYUELA


class TestValidacionesDeNegocio:

    def test_evita_duplicados(self, ctx):
        with pytest.raises(DuplicadoError):
            ctx.socios.crear("Otra", "Persona", "30.111.222")
        with pytest.raises(DuplicadoError):
            ctx.catalogo.crear_libro("978-0-8021-3030-3", "Dup", "X")
        with pytest.raises(DuplicadoError):
            ctx.catalogo.crear_ejemplar(ISBN_FICCIONES, ctx.central.id,
                                        ctx.ej_central.codigo_inventario)
        with pytest.raises(DuplicadoError):
            ctx.sedes.crear("central", "Otra dirección")

    def test_no_presta_a_socio_inhabilitado(self, ctx):
        ctx.socios.inhabilitar(ctx.ana.id, "Multas impagas")
        with pytest.raises(ReglaNegocioError, match="inhabilitado"):
            ctx.prestamos.solicitar(ctx.ana.id, ctx.ej_central.id,
                                    ctx.central.id, ctx.central.id)

    def test_no_presta_ejemplar_no_disponible(self, ctx):
        ctx.prestamos.solicitar(ctx.ana.id, ctx.ej_central.id,
                                ctx.central.id, ctx.central.id)
        with pytest.raises(ReglaNegocioError, match="no está disponible"):
            ctx.prestamos.solicitar(ctx.beto.id, ctx.ej_central.id,
                                    ctx.central.id, ctx.central.id)

    def test_ejemplar_debe_pertenecer_a_sede_origen(self, ctx):
        with pytest.raises(ReglaNegocioError, match="no pertenece"):
            ctx.prestamos.solicitar(ctx.ana.id, ctx.ej_norte.id,
                                    ctx.central.id, ctx.central.id)

    def test_sede_de_baja_bloquea_prestamos_y_envios(self, ctx):
        ctx.sedes.dar_de_baja(ctx.norte.id)
        with pytest.raises(ReglaNegocioError, match="dada de baja"):
            ctx.prestamos.solicitar(ctx.ana.id, ctx.ej_central.id,
                                    ctx.central.id, ctx.norte.id)
        with pytest.raises(ReglaNegocioError, match="dada de baja"):
            ctx.reservas.crear(ctx.ana.id, ISBN_RAYUELA, ctx.norte.id)

    def test_no_da_de_baja_sede_con_operaciones_en_curso(self, ctx):
        ctx.prestamos.solicitar(ctx.ana.id, ctx.ej_central.id,
                                ctx.central.id, ctx.norte.id)
        with pytest.raises(ReglaNegocioError, match="remitos en curso"):
            ctx.sedes.dar_de_baja(ctx.norte.id)

    def test_socio_con_vencidos_no_puede_pedir_mas(self, ctx):
        ctx.prestamos.solicitar(ctx.ana.id, ctx.ej_central.id,
                                ctx.central.id, ctx.central.id)
        ctx.reloj.avanzar(dias=20)
        otro = ctx.catalogo.crear_ejemplar(ISBN_RAYUELA, ctx.central.id)
        with pytest.raises(ReglaNegocioError, match="vencido"):
            ctx.prestamos.solicitar(ctx.ana.id, otro.id, ctx.central.id,
                                    ctx.central.id)


class TestPrestamoLocal:

    def test_devolucion_con_atraso_y_dano(self, ctx):
        p = ctx.prestamos.solicitar(ctx.ana.id, ctx.ej_central.id,
                                    ctx.central.id, ctx.central.id)
        assert p.tipo == TipoPrestamo.LOCAL and p.estado == EstadoPrestamo.ACTIVO
        assert ctx.ejemplar(ctx.ej_central).estado == EstadoEjemplar.EN_PRESTAMO
        ctx.reloj.avanzar(dias=17)            # 14 de plazo + 3 de atraso
        p = ctx.prestamos.registrar_devolucion(p.id, "DANADA")
        assert p.multa == 3 * 500 + 15000
        assert ctx.ejemplar(ctx.ej_central).estado == EstadoEjemplar.DANADO
        notifs = ctx.socios.notificaciones(ctx.ana.id)
        assert "multa" in notifs[0].mensaje


class TestPrestamoInterbibliotecario:

    def test_flujo_completo_con_retorno(self, ctx):
        p = ctx.prestamos.solicitar(ctx.ana.id, ctx.ej_central.id,
                                    ctx.central.id, ctx.norte.id)
        assert p.estado == EstadoPrestamo.PENDIENTE_ENVIO
        assert ctx.ejemplar(ctx.ej_central).estado == EstadoEjemplar.RESERVADO

        envio = ctx.remito_de(p)
        ctx.completar_envio(envio)
        ej = ctx.ejemplar(ctx.ej_central)
        assert ej.sede_actual_id == ctx.norte.id and ej.sede_id == ctx.central.id
        assert ctx.prestamos.obtener(p.id).estado == \
            EstadoPrestamo.LISTO_PARA_RETIRO
        assert len(ctx.uow.remitos.obtener(envio.id).historial) == 5

        p = ctx.prestamos.entregar(p.id)
        assert p.fecha_vencimiento is not None
        ctx.prestamos.registrar_devolucion(p.id, "BUENA")
        assert ctx.ejemplar(ctx.ej_central).estado == EstadoEjemplar.RESERVADO

        retorno = ctx.remito_de(p, "RETORNO")
        assert retorno.sede_origen_id == ctx.norte.id
        ctx.completar_envio(retorno)
        ej = ctx.ejemplar(ctx.ej_central)
        assert ej.estado == EstadoEjemplar.DISPONIBLE
        assert ej.sede_actual_id == ctx.central.id

        mensajes = [n.mensaje for n in ctx.socios.notificaciones(ctx.ana.id)]
        assert any("ya podés retirarlo" in m for m in mensajes)

    def test_cancelar_antes_de_despachar_libera_ejemplar(self, ctx):
        p = ctx.prestamos.solicitar(ctx.ana.id, ctx.ej_central.id,
                                    ctx.central.id, ctx.norte.id)
        ctx.prestamos.cancelar(p.id, "El socio desistió")
        assert ctx.prestamos.obtener(p.id).estado == EstadoPrestamo.CANCELADO
        assert ctx.ejemplar(ctx.ej_central).estado == EstadoEjemplar.DISPONIBLE

    def test_no_cancela_si_ya_fue_despachado(self, ctx):
        p = ctx.prestamos.solicitar(ctx.ana.id, ctx.ej_central.id,
                                    ctx.central.id, ctx.norte.id)
        envio = ctx.remito_de(p)
        ctx.logistica.operar(envio.id, "empaquetar")
        ctx.logistica.operar(envio.id, "despachar")
        with pytest.raises(ReglaNegocioError, match="despachado"):
            ctx.prestamos.cancelar(p.id, "x")

    def test_extravio_da_de_baja_ejemplar_y_cancela_prestamo(self, ctx):
        p = ctx.prestamos.solicitar(ctx.ana.id, ctx.ej_central.id,
                                    ctx.central.id, ctx.norte.id)
        envio = ctx.remito_de(p)
        ctx.logistica.operar(envio.id, "empaquetar")
        ctx.logistica.operar(envio.id, "despachar")
        ctx.logistica.operar(envio.id, "reportar_incidencia",
                             tipo_incidencia="EXTRAVIO",
                             observacion="Paquete no localizado")
        ctx.logistica.operar(envio.id, "declarar_extravio")
        assert ctx.ejemplar(ctx.ej_central).estado == EstadoEjemplar.BAJA
        assert ctx.prestamos.obtener(p.id).estado == EstadoPrestamo.CANCELADO

    def test_operacion_invalida_para_el_estado(self, ctx):
        p = ctx.prestamos.solicitar(ctx.ana.id, ctx.ej_central.id,
                                    ctx.central.id, ctx.norte.id)
        with pytest.raises(TransicionInvalidaError):
            ctx.logistica.operar(ctx.remito_de(p).id, "recibir")


class TestReservas:

    def test_cola_fifo_y_concretar(self, ctx):
        ctx.prestamos.solicitar(ctx.ana.id, ctx.ej_central.id,
                                ctx.central.id, ctx.central.id)
        r = ctx.reservas.crear(ctx.beto.id, ISBN_FICCIONES, ctx.central.id)
        assert r.estado == EstadoReserva.PENDIENTE
        with pytest.raises(DuplicadoError):
            ctx.reservas.crear(ctx.beto.id, ISBN_FICCIONES, ctx.central.id)

        prestamo_ana = ctx.uow.prestamos.abiertos_de_socio(ctx.ana.id)[0]
        ctx.prestamos.registrar_devolucion(prestamo_ana.id, "BUENA")
        r = ctx.reservas.obtener(r.id)
        assert r.estado == EstadoReserva.DISPONIBLE
        assert ctx.ejemplar(ctx.ej_central).estado == EstadoEjemplar.RESERVADO

        # Otro socio no puede llevarse el ejemplar reservado.
        with pytest.raises(ReglaNegocioError):
            ctx.prestamos.solicitar(ctx.ana.id, ctx.ej_central.id,
                                    ctx.central.id, ctx.central.id)
        p = ctx.prestamos.concretar_reserva(r.id)
        assert p.socio_id == ctx.beto.id
        assert ctx.reservas.obtener(r.id).estado == EstadoReserva.CUMPLIDA

    def test_reserva_vencida_libera_ejemplar(self, ctx):
        r = ctx.reservas.crear(ctx.ana.id, ISBN_FICCIONES, ctx.central.id)
        assert r.estado == EstadoReserva.DISPONIBLE
        ctx.reloj.avanzar(dias=5)
        assert ctx.reservas.procesar_vencidas() == 1
        assert ctx.ejemplar(ctx.ej_central).estado == EstadoEjemplar.DISPONIBLE


class TestReportes:

    def test_reportes_calculan(self, ctx):
        p = ctx.prestamos.solicitar(ctx.ana.id, ctx.ej_central.id,
                                    ctx.central.id, ctx.norte.id)
        ctx.completar_envio(ctx.remito_de(p))
        ctx.prestamos.entregar(p.id)
        ctx.reloj.avanzar(dias=30)
        reportes = ReporteService(ConsultasSQLite(ctx.uow.conexion), ctx.reloj)

        vencidos = reportes.vencidos_y_multas()
        assert len(vencidos["detalle"]) == 1
        assert vencidos["total_estimado"] > 0

        logistica = reportes.logistica()
        assert logistica["indicadores"]["tasa_exito"] == 100.0
        assert logistica["indicadores"]["horas_promedio_transito"] == 12.0

        ranking = reportes.libros_mas_solicitados()["ranking"]
        assert ranking[0]["isbn"] == ISBN_FICCIONES

        activos = reportes.prestamos_activos_y_transito()
        assert activos["totales"]["activos_interbib"] == 1
        assert reportes.disponibilidad_por_sede()
