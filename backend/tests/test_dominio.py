"""Tests unitarios del dominio (sin base de datos)."""

from datetime import date, datetime

import pytest

from domain.enums import CondicionFisica, TipoIncidencia
from domain.excepciones import (DatoInvalidoError, ReglaNegocioError,
                                TransicionInvalidaError)
from domain.libro import ISBN
from domain.multas import MultaEscalonada, MultaLineal
from domain.remito import ContextoTransicion, Remito
from domain.sede import Sede
from domain.socio import Socio
from tests.conftest import direccion

T0 = datetime(2026, 1, 1, 9, 0)


def ctx(hora, **kw):
    return ContextoTransicion(fecha_hora=T0.replace(hour=hora), **kw)


def nuevo_remito():
    return Remito(1, 1, 2, "ENVIO", T0, prestamo_id=1, id=7)


class TestRemitoState:

    def test_ciclo_feliz_y_trazabilidad(self):
        r = nuevo_remito()
        assert r.estado == "CREADO"
        r.empaquetar(ctx(10))
        r.despachar(ctx(11))
        r.registrar_checkpoint(ctx(12, ubicacion="Centro de distribución"))
        r.registrar_checkpoint(ctx(13, ubicacion="Ruta 9 km 20"))
        r.recibir(ctx(14, condicion=CondicionFisica.BUENA))
        assert r.estado == "RECIBIDO" and r.finalizado
        assert [m.estado for m in r.historial] == [
            "CREADO", "EMPAQUETADO", "DESPACHADO", "EN_TRANSITO",
            "EN_TRANSITO", "RECIBIDO"]
        assert r.acciones_disponibles == []
        assert len(r.extraer_eventos()) == 5

    def test_no_se_puede_despachar_sin_empaquetar(self):
        with pytest.raises(TransicionInvalidaError):
            nuevo_remito().despachar(ctx(10))

    def test_no_se_puede_cancelar_luego_de_despachar(self):
        r = nuevo_remito()
        r.empaquetar(ctx(10))
        r.despachar(ctx(11))
        with pytest.raises(TransicionInvalidaError):
            r.cancelar(ctx(12, observacion="x"))

    def test_incidencia_resuelta_y_extravio(self):
        r = nuevo_remito()
        r.empaquetar(ctx(10))
        r.despachar(ctx(11))
        r.reportar_incidencia(ctx(12, tipo_incidencia=TipoIncidencia.DEMORA,
                                  observacion="Corte de ruta"))
        assert r.acciones_disponibles == [
            "recibir", "resolver_incidencia", "declarar_extravio"]
        r.resolver_incidencia(ctx(13))
        assert r.estado == "EN_TRANSITO" and r.tuvo_incidencias
        r.reportar_incidencia(ctx(14, tipo_incidencia="EXTRAVIO",
                                  observacion="No llegó"))
        r.declarar_extravio(ctx(15))
        assert r.estado == "EXTRAVIADO" and r.finalizado

    def test_acciones_por_estado(self):
        r = nuevo_remito()
        assert r.acciones_disponibles == ["empaquetar", "cancelar"]

    def test_no_acepta_fechas_hacia_atras(self):
        r = nuevo_remito()
        r.empaquetar(ctx(12))
        with pytest.raises(ReglaNegocioError):
            r.despachar(ctx(11))

    def test_origen_y_destino_distintos(self):
        with pytest.raises(DatoInvalidoError):
            Remito(1, 3, 3, "ENVIO", T0)


class TestValueObjectsYEntidades:

    def test_isbn_valida_digito_control(self):
        assert ISBN("978-0-306-40615-7").valor == "9780306406157"
        assert ISBN("0-306-40615-2").valor == "0306406152"
        with pytest.raises(DatoInvalidoError):
            ISBN("9780306406158")

    def test_sede_de_baja_no_opera(self):
        sede = Sede("Sur", direccion("Calle Uno", "1"))
        sede.dar_de_baja()
        with pytest.raises(ReglaNegocioError):
            sede.verificar_operativa()

    def test_socio_inhabilitado_no_opera(self):
        socio = Socio("Ana", "Paz", "30.111.222")
        assert socio.documento == "30111222"
        socio.inhabilitar("Deuda")
        with pytest.raises(ReglaNegocioError):
            socio.verificar_puede_operar()


class TestMultasStrategy:

    def test_lineal(self):
        assert MultaLineal(500).calcular_total(4) == 2000

    def test_escalonada_duplica_despues_del_umbral(self):
        politica = MultaEscalonada(500, umbral_dias=7, factor=2)
        assert politica.calcular_total(10) == 7 * 500 + 3 * 1000

    def test_recargo_por_dano(self):
        assert MultaLineal(500).calcular_total(
            0, CondicionFisica.DANADA) == 15000


class TestValidacionesDeFormato:

    def test_nombres_sin_numeros_y_telefono_sin_letras(self):
        with pytest.raises(DatoInvalidoError, match="letras"):
            Socio("Ana2", "Paz", "30111222")
        with pytest.raises(DatoInvalidoError, match="teléfono"):
            Socio("Ana", "Paz", "30111222", telefono="351-ABC")
        with pytest.raises(DatoInvalidoError, match="email"):
            Socio("Ana", "Paz", "30111222", email="ana@mail")
        assert Socio("María José", "D'Angelo", "30111222",
                     telefono="+54 (351) 456-7890").telefono

    def test_horario_rechaza_franjas_superpuestas(self):
        franjas = [{"dias": [0, 1], "desde": "08:00", "hasta": "13:00"},
                   {"dias": [1], "desde": "12:00", "hasta": "18:00"}]
        with pytest.raises(DatoInvalidoError, match="superpuestas"):
            Sede("Sur", direccion(), horario=franjas)
        sede = Sede("Sur", direccion(), horario=[
            {"dias": [0, 1, 2, 3, 4], "desde": "08:00", "hasta": "20:00"},
            {"dias": [5], "desde": "09:00", "hasta": "13:00"}])
        assert sede.horario.texto == ("Lun a Vie 08:00 a 20:00 · "
                                      "Sáb 09:00 a 13:00")

    def test_direccion_valida_altura_y_provincia(self):
        with pytest.raises(DatoInvalidoError, match="altura"):
            Sede("Sur", direccion(numero="12a"))
        with pytest.raises(DatoInvalidoError, match="Provincia"):
            Sede("Sur", {**direccion(), "provincia": "Narnia"})
