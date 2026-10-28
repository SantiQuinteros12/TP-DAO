"""Tests end-to-end de la API REST."""

import pytest
from fastapi.testclient import TestClient

import config
from main import crear_app
from tests.conftest import direccion


@pytest.fixture
def api(tmp_path, monkeypatch):
    monkeypatch.setattr(config, "RUTA_DB", str(tmp_path / "api.db"))
    with TestClient(crear_app()) as cliente:
        yield cliente


def test_flujo_interbibliotecario_por_http(api):
    central = api.post("/api/sedes", json={"nombre": "Central",
                                           "direccion": direccion("Colón", "1")}).json()
    norte = api.post("/api/sedes", json={"nombre": "Norte",
                                         "direccion": direccion("Andes", "2")}).json()
    socio = api.post("/api/socios", json={"nombre": "Ana", "apellido": "Paz",
                                          "documento": "30111222"}).json()
    api.post("/api/libros", json={"isbn": "9780802130303",
                                  "titulo": "Ficciones", "autor": "Borges"})
    ej = api.post("/api/ejemplares", json={"isbn": "9780802130303",
                                           "sede_id": central["id"]}).json()

    r = api.post("/api/prestamos", json={
        "socio_id": socio["id"], "ejemplar_id": ej["id"],
        "sede_origen_id": central["id"], "sede_destino_id": norte["id"]})
    assert r.status_code == 201, r.text
    prestamo = r.json()
    assert prestamo["tipo"] == "INTERBIBLIOTECARIO"

    remito_id = api.get(f"/api/prestamos/{prestamo['id']}").json()[
        "remitos"][0]["id"]
    # Transición inválida -> 409 con el mensaje del dominio
    r = api.post(f"/api/remitos/{remito_id}/acciones/recibir")
    assert r.status_code == 409
    assert "CREADO" in r.json()["detail"]

    for accion, cuerpo in (("empaquetar", {}), ("despachar", {}),
                           ("registrar_checkpoint", {"ubicacion": "Ruta"}),
                           ("recibir", {"condicion": "BUENA"})):
        r = api.post(f"/api/remitos/{remito_id}/acciones/{accion}",
                     json=cuerpo)
        assert r.status_code == 200, r.text
    remito = r.json()
    assert remito["estado"] == "RECIBIDO"
    assert [m["estado"] for m in remito["historial"]][-1] == "RECIBIDO"

    assert api.post(f"/api/prestamos/{prestamo['id']}/entregar").json()[
        "estado"] == "ACTIVO"
    notifs = api.get(f"/api/socios/{socio['id']}/notificaciones").json()
    assert len(notifs) >= 2

    for ruta in ("resumen", "prestamos-activos", "vencidos",
                 "libros-mas-solicitados", "disponibilidad-sedes",
                 "logistica"):
        assert api.get(f"/api/reportes/{ruta}").status_code == 200


def test_errores_de_negocio_y_rollback(api):
    api.post("/api/sedes", json={"nombre": "Central", "direccion": direccion("Calle x", "1")})
    r = api.post("/api/sedes", json={"nombre": "CENTRAL", "direccion": direccion("Calle y", "2")})
    assert r.status_code == 409
    assert api.get("/api/sedes/99").status_code == 404
    r = api.post("/api/libros", json={"isbn": "123", "titulo": "t",
                                      "autor": "a"})
    assert r.status_code == 400
    assert len(api.get("/api/sedes").json()) == 1
