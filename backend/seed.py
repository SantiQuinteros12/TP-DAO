"""
Genera una base de datos de demostración.

En lugar de insertar filas a mano, simula ~4 meses de operación usando los
mismos servicios que la API con un reloj controlado (RelojFijo): así todos
los datos respetan las reglas de negocio y los reportes muestran
información realista (vencidos, incidencias, tiempos de tránsito, etc.).

Uso (desde la carpeta backend)::

    python seed.py            # crea la base si no existe
    python seed.py --reset    # la borra y la vuelve a generar
"""

import random
import sys
from datetime import datetime, timedelta
from pathlib import Path

import config
from domain.enums import EstadoEjemplar, EstadoPrestamo, EstadoReserva
from domain.excepciones import ErrorDominio
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

DIAS_SIMULADOS = 120

SEDES = [
    ("Biblioteca Central", "Av. Colón 1250, Córdoba", "0351-4331100",
     "central@bibliored.org", "Lun a Vie 8 a 20 - Sáb 9 a 13"),
    ("Sede Nueva Córdoba", "Bv. Illia 350, Córdoba", "0351-4605522",
     "nuevacba@bibliored.org", "Lun a Vie 9 a 19"),
    ("Sede Cerro de las Rosas", "Av. Rafael Núñez 4100, Córdoba",
     "0351-4812233", "cerro@bibliored.org", "Lun a Vie 10 a 18"),
    ("Sede Alta Córdoba", "Jerónimo Luis de Cabrera 690, Córdoba",
     "0351-4710044", "altacba@bibliored.org", "Mar a Sáb 9 a 17"),
    ("Sede Güemes", "Belgrano 820, Córdoba", "0351-4689900",
     "guemes@bibliored.org", "Cerrada por remodelación"),
]

LIBROS = [
    ("9780307474728", "Cien años de soledad", "Gabriel García Márquez",
     "Vintage Español", 1967, "Novela"),
    ("9788437604572", "Rayuela", "Julio Cortázar", "Cátedra", 1963,
     "Novela"),
    ("9780802130303", "Ficciones", "Jorge Luis Borges", "Grove Press", 1944,
     "Cuentos"),
    ("9788499089508", "El Aleph", "Jorge Luis Borges", "Debolsillo", 1949,
     "Cuentos"),
    ("9788420412146", "Don Quijote de la Mancha", "Miguel de Cervantes",
     "Alfaguara", 1605, "Clásico"),
    ("9780451524935", "1984", "George Orwell", "Signet", 1949, "Distopía"),
    ("9780156012195", "El principito", "Antoine de Saint-Exupéry",
     "Harcourt", 1943, "Infantil"),
    ("9789500203555", "Martín Fierro", "José Hernández", "Eudeba", 1872,
     "Poesía"),
    ("9789505470327", "Sobre héroes y tumbas", "Ernesto Sabato",
     "Seix Barral", 1961, "Novela"),
    ("9788437604947", "Pedro Páramo", "Juan Rulfo", "Cátedra", 1955,
     "Novela"),
    ("9789875666474", "Las venas abiertas de América Latina",
     "Eduardo Galeano", "Siglo XXI", 1971, "Ensayo"),
    ("9788420471839", "La ciudad y los perros", "Mario Vargas Llosa",
     "Alfaguara", 1963, "Novela"),
]

# (índice de libro, índices de sedes donde hay ejemplares)
EJEMPLARES = {
    0: [0, 0, 1, 2], 1: [0, 2, 3], 2: [0, 1, 3], 3: [1, 2], 4: [0, 0, 2, 3],
    5: [1, 2, 3], 6: [0, 1, 2, 3], 7: [0, 4], 8: [2, 0], 9: [3, 1],
    10: [0, 1], 11: [1, 3],
}

SOCIOS = [
    ("Lucía", "Fernández", "35123456"), ("Martín", "Gómez", "33987654"),
    ("Sofía", "Rodríguez", "40111222"), ("Joaquín", "Pérez", "38555666"),
    ("Valentina", "López", "42333444"), ("Tomás", "Díaz", "36777888"),
    ("Camila", "Martínez", "41222999"), ("Mateo", "Sánchez", "39444111"),
    ("Julieta", "Romero", "37666333"), ("Nicolás", "Torres", "34888222"),
    ("Agustina", "Álvarez", "43111777"), ("Facundo", "Ruiz", "32999555"),
    ("Florencia", "Herrera", "40777444"), ("Bruno", "Castro", "38222111"),
]

RESPONSABLES = ["M. Ibáñez", "C. Ortega", "P. Molina", "R. Vega"]
UBICACIONES = ["Centro de distribución Córdoba", "Camioneta interna #2",
               "Depósito Av. Colón", "Control de ruta Bv. San Juan"]


class Simulacion:

    def __init__(self, uow, reloj):
        pub = crear_publicador()
        self.uow, self.reloj = uow, reloj
        self.sedes = SedeService(uow, reloj, pub)
        self.socios = SocioService(uow, reloj, pub)
        self.catalogo = CatalogoService(uow, reloj, pub)
        self.prestamos = PrestamoService(uow, reloj, pub)
        self.reservas = ReservaService(uow, reloj, pub)
        self.logistica = LogisticaService(uow, reloj, pub)
        self.rnd = random.Random(2026)

    def intentar(self, accion, *args, **kwargs):
        """Las operaciones que violan reglas simplemente se descartan."""
        try:
            return accion(*args, **kwargs)
        except ErrorDominio:
            return None

    def cargar_maestros(self):
        sedes = [self.sedes.crear(*s) for s in SEDES]
        for libro in LIBROS:
            self.catalogo.crear_libro(*libro)
        for i_libro, i_sedes in EJEMPLARES.items():
            for i_sede in i_sedes:
                self.catalogo.crear_ejemplar(LIBROS[i_libro][0],
                                             sedes[i_sede].id)
        for nombre, apellido, dni in SOCIOS:
            self.socios.crear(nombre, apellido, dni,
                              f"{nombre.lower()}.{apellido.lower()}@mail.com",
                              f"351-5{dni[-6:]}")
        self.sedes_activas = [s.id for s in sedes[:4]]
        self.sede_baja = sedes[4].id
        self.socios_ids = [s.id for s in self.socios.listar()]
        self.morosos = set(self.socios_ids[:3])

    # --- una jornada ----------------------------------------------------
    def jornada(self, dia):
        self.reloj.fijar(dia.replace(hour=9))
        for _ in range(self.rnd.randint(0, 2)):
            self.nuevo_prestamo(interbibliotecario=False)
        for _ in range(self.rnd.randint(0, 2)):
            self.nuevo_prestamo(interbibliotecario=True)
        if self.rnd.random() < 0.25:
            self.nueva_reserva()

        for hora in (11, 15, 18):
            self.reloj.fijar(dia.replace(hour=hora,
                                         minute=self.rnd.randint(0, 59)))
            self.avanzar_remitos()

        self.reloj.fijar(dia.replace(hour=17))
        self.atender_mostrador()
        self.reservas.procesar_vencidas()

    def nuevo_prestamo(self, interbibliotecario):
        disponibles = self.uow.ejemplares.listar(
            estado=EstadoEjemplar.DISPONIBLE)
        disponibles = [e for e in disponibles if e.esta_en_su_sede]
        if not disponibles:
            return
        ejemplar = self.rnd.choice(disponibles)
        destino = ejemplar.sede_id
        if interbibliotecario:
            destino = self.rnd.choice(
                [s for s in self.sedes_activas if s != ejemplar.sede_id])
        self.intentar(self.prestamos.solicitar,
                      self.rnd.choice(self.socios_ids), ejemplar.id,
                      ejemplar.sede_id, destino)

    def nueva_reserva(self):
        prestados = self.uow.ejemplares.listar(
            estado=EstadoEjemplar.EN_PRESTAMO)
        if prestados:
            ejemplar = self.rnd.choice(prestados)
            self.intentar(self.reservas.crear,
                          self.rnd.choice(self.socios_ids), ejemplar.isbn,
                          ejemplar.sede_id)

    def avanzar_remitos(self):
        for remito in self.uow.remitos.listar():
            if remito.finalizado or self.rnd.random() < 0.45:
                continue
            datos = {"responsable": self.rnd.choice(RESPONSABLES)}
            acciones = remito.acciones_disponibles
            azar = self.rnd.random()
            if remito.estado == "CON_INCIDENCIA":
                ultima = remito.historial[-1]
                if ultima.tipo_incidencia == "EXTRAVIO":
                    op = "declarar_extravio"
                elif ultima.tipo_incidencia == "DANO":
                    op, datos["condicion"] = "recibir", "DANADA"
                else:
                    op = "resolver_incidencia"
                    datos["observacion"] = "Se retomó el recorrido"
            elif ("reportar_incidencia" in acciones
                  and not remito.tuvo_incidencias and azar < 0.04):
                op = "reportar_incidencia"
                tipo = self.rnd.choices(["DEMORA", "DANO", "EXTRAVIO"],
                                        [10, 3, 1])[0]
                datos.update(tipo_incidencia=tipo, observacion={
                    "DEMORA": "Demora por corte de calle",
                    "DANO": "Paquete con signos de humedad",
                    "EXTRAVIO": "El bulto no figura en la carga"}[tipo])
            elif remito.estado == "DESPACHADO" or (
                    remito.estado == "EN_TRANSITO" and azar < 0.25):
                op = "registrar_checkpoint"
                datos["ubicacion"] = self.rnd.choice(UBICACIONES)
            elif remito.estado == "EN_TRANSITO":
                op, datos["condicion"] = "recibir", "BUENA"
            else:
                op = acciones[0]    # empaquetar / despachar
            self.intentar(self.logistica.operar, remito.id, op, **datos)

    def atender_mostrador(self):
        hoy = self.reloj.hoy()
        for p in self.uow.prestamos.listar(
                estado=EstadoPrestamo.LISTO_PARA_RETIRO):
            if self.rnd.random() < 0.6:
                self.intentar(self.prestamos.entregar, p.id)
        for p in self.uow.prestamos.listar(estado=EstadoPrestamo.ACTIVO):
            dias = (hoy - p.fecha_inicio).days
            # La mayoría devuelve en plazo; los morosos se atrasan.
            prob = 0.015 if p.socio_id in self.morosos else 0.09
            if dias >= 4 and self.rnd.random() < prob:
                condicion = self.rnd.choices(
                    ["BUENA", "DETERIORADA", "DANADA"], [92, 6, 2])[0]
                self.intentar(self.prestamos.registrar_devolucion, p.id,
                              condicion)
        for e in self.uow.ejemplares.listar(estado=EstadoEjemplar.DANADO):
            if e.esta_en_su_sede and self.rnd.random() < 0.15:
                self.intentar(self.catalogo.reparar_ejemplar, e.id)
        for r in self.uow.reservas.listar(estado=EstadoReserva.DISPONIBLE):
            if self.rnd.random() < 0.5:
                self.intentar(self.prestamos.concretar_reserva, r.id)

    def ejecutar(self, hasta):
        self.cargar_maestros()
        self.sedes.dar_de_baja(self.sede_baja)
        inicio = hasta - timedelta(days=DIAS_SIMULADOS)
        for n in range(DIAS_SIMULADOS):
            self.jornada(inicio + timedelta(days=n))
        socio = self.socios.listar(texto="Castro")[0]
        self.socios.inhabilitar(socio.id, "Adeuda material dañado")


def main():
    ruta = Path(config.RUTA_DB)
    if ruta.exists():
        if "--reset" not in sys.argv:
            print(f"La base {ruta} ya existe. Use --reset para regenerarla.")
            return
        ruta.unlink()
    ruta.parent.mkdir(parents=True, exist_ok=True)
    inicializar_esquema(str(ruta))

    ahora = datetime.now().replace(minute=0, second=0, microsecond=0)
    reloj = RelojFijo(ahora - timedelta(days=DIAS_SIMULADOS + 1))
    with UnidadDeTrabajoSQLite(str(ruta)) as uow:
        Simulacion(uow, reloj).ejecutar(hasta=ahora.replace(hour=0))
    print(f"Base de demostración generada en {ruta}")


if __name__ == "__main__":
    main()
