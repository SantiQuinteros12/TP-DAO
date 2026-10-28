from datetime import datetime

import pytest

from domain.reloj import RelojFijo
from infrastructure.database import inicializar_esquema
from infrastructure.repositorios_sqlite import UnidadDeTrabajoSQLite
from services.catalogo_service import CatalogoService
from services.logistica_service import LogisticaService
from services.notificaciones import crear_publicador
from services.prestamo_service import PrestamoService
from services.reserva_service import ReservaService
from services.sede_service import SedeService
from services.socio_service import SocioService

ISBN_FICCIONES = "9780802130303"


def direccion(calle="Av. Colón", numero="100"):
    return {"calle": calle, "numero": numero, "ciudad": "Córdoba",
            "provincia": "Córdoba"}


ISBN_RAYUELA = "9788437604572"


class Contexto:
    """Agrupa uow, reloj y servicios para los tests."""

    def __init__(self, ruta_db):
        inicializar_esquema(ruta_db)
        self.uow = UnidadDeTrabajoSQLite(ruta_db)
        self.reloj = RelojFijo(datetime(2026, 3, 2, 10, 0))
        pub = crear_publicador()
        args = (self.uow, self.reloj, pub)
        self.sedes = SedeService(*args)
        self.socios = SocioService(*args)
        self.catalogo = CatalogoService(*args)
        self.prestamos = PrestamoService(*args)
        self.reservas = ReservaService(*args)
        self.logistica = LogisticaService(*args)

        self.central = self.sedes.crear("Central", direccion("Av. Colón", "100"))
        self.norte = self.sedes.crear("Norte", direccion("Bv. Los Andes", "50"))
        self.ana = self.socios.crear("Ana", "García", "30111222")
        self.beto = self.socios.crear("Beto", "López", "31222333")
        self.catalogo.crear_libro(ISBN_FICCIONES, "Ficciones", "J. L. Borges")
        self.catalogo.crear_libro(ISBN_RAYUELA, "Rayuela", "J. Cortázar")
        self.ej_central = self.catalogo.crear_ejemplar(ISBN_FICCIONES,
                                                       self.central.id)
        self.ej_norte = self.catalogo.crear_ejemplar(ISBN_RAYUELA,
                                                     self.norte.id)

    def ejemplar(self, ejemplar):
        return self.uow.ejemplares.obtener(ejemplar.id)

    def remito_de(self, prestamo, tipo="ENVIO"):
        return next(r for r in self.uow.remitos.de_prestamo(prestamo.id)
                    if r.tipo.value == tipo)

    def completar_envio(self, remito):
        for op, extra in (("empaquetar", {}), ("despachar", {}),
                          ("registrar_checkpoint", {"ubicacion": "Ruta 9"}),
                          ("recibir", {})):
            self.reloj.avanzar(horas=6)
            self.logistica.operar(remito.id, op, responsable="test", **extra)


@pytest.fixture
def ctx(tmp_path):
    contexto = Contexto(str(tmp_path / "test.db"))
    yield contexto
    contexto.uow.cerrar()
