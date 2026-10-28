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

def _dir(calle, numero, barrio, cp):
    return {"calle": calle, "numero": numero, "barrio": barrio,
            "ciudad": "Córdoba", "provincia": "Córdoba",
            "codigo_postal": cp}


def _franja(desde_dia, hasta_dia, desde, hasta):
    return {"dias": list(range(desde_dia, hasta_dia + 1)),
            "desde": desde, "hasta": hasta}


SEDES = [
    ("Biblioteca Central", _dir("Av. Colón", "1250", "Centro", "X5000"),
     "0351-4331100", "central@bibliored.org",
     [_franja(0, 4, "08:00", "20:00"), _franja(5, 5, "09:00", "13:00")]),
    ("Sede Nueva Córdoba", _dir("Bv. Illia", "350", "Nueva Córdoba",
                                "X5000"),
     "0351-4605522", "nuevacba@bibliored.org",
     [_franja(0, 4, "09:00", "19:00")]),
    ("Sede Cerro de las Rosas", _dir("Av. Rafael Núñez", "4100",
                                     "Cerro de las Rosas", "X5009"),
     "0351-4812233", "cerro@bibliored.org",
     [_franja(0, 4, "10:00", "18:00")]),
    ("Sede Alta Córdoba", _dir("Jerónimo Luis de Cabrera", "690",
                               "Alta Córdoba", "X5001"),
     "0351-4710044", "altacba@bibliored.org",
     [_franja(1, 5, "09:00", "17:00")]),
    ("Sede Güemes", _dir("Belgrano", "820", "Güemes", "X5000"),
     "0351-4689900", "guemes@bibliored.org", []),
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

def _isbn(base12):
    """Completa un ISBN-13 de demostración con su dígito de control."""
    suma = sum(int(c) * (1 if i % 2 == 0 else 3) for i, c in enumerate(base12))
    return base12 + str((10 - suma % 10) % 10)


LIBROS += [
    (_isbn("978950070001"), "El túnel", "Ernesto Sabato", "Seix Barral",
     1948, "Novela"),
    (_isbn("978950070002"), "Bestiario", "Julio Cortázar", "Sudamericana",
     1951, "Cuentos"),
    (_isbn("978950070003"), "El libro de arena", "Jorge Luis Borges",
     "Emecé", 1975, "Cuentos"),
    (_isbn("978950070004"), "Crónica de una muerte anunciada",
     "Gabriel García Márquez", "Sudamericana", 1981, "Novela"),
    (_isbn("978950070005"), "Rebelión en la granja", "George Orwell",
     "Debolsillo", 1945, "Distopía"),
    (_isbn("978950070006"), "Fahrenheit 451", "Ray Bradbury", "Minotauro",
     1953, "Distopía"),
    (_isbn("978950070007"), "Un mundo feliz", "Aldous Huxley", "Debolsillo",
     1932, "Distopía"),
    (_isbn("978950070008"), "Facundo", "Domingo F. Sarmiento", "Eudeba",
     1845, "Ensayo"),
    (_isbn("978950070009"), "Operación masacre", "Rodolfo Walsh",
     "De la Flor", 1957, "Ensayo"),
    (_isbn("978950070010"), "Cuentos de la selva", "Horacio Quiroga",
     "Losada", 1918, "Infantil"),
    (_isbn("978950070011"), "Veinte poemas de amor", "Pablo Neruda",
     "Seix Barral", 1924, "Poesía"),
    (_isbn("978950070012"), "Hamlet", "William Shakespeare", "Austral",
     1603, "Clásico"),
    (_isbn("978950070013"), "La metamorfosis", "Franz Kafka", "Alianza",
     1915, "Clásico"),
    (_isbn("978950070014"), "El amor en los tiempos del cólera",
     "Gabriel García Márquez", "Sudamericana", 1985, "Novela"),
]


# (índice de libro, índices de sedes donde hay ejemplares)
EJEMPLARES = {
    0: [0, 0, 1, 2], 1: [0, 2, 3], 2: [0, 1, 3], 3: [1, 2], 4: [0, 0, 2, 3],
    5: [1, 2, 3], 6: [0, 1, 2, 3], 7: [0, 4], 8: [2, 0], 9: [3, 1],
    10: [0, 1], 11: [1, 3], 12: [0, 2], 13: [1, 3], 14: [0, 2],
    15: [0, 1, 3], 16: [2, 3], 17: [0, 1], 18: [1, 2], 19: [0, 3],
    20: [2, 1], 21: [0, 3], 22: [1, 2], 23: [0, 2], 24: [3, 0],
    25: [0, 1, 2],
}

SOCIOS = [
    ("Lucía", "Fernández", "35123456"), ("Martín", "Gómez", "33987654"),
    ("Sofía", "Rodríguez", "40111222"), ("Joaquín", "Pérez", "38555666"),
    ("Valentina", "López", "42333444"), ("Tomás", "Díaz", "36777888"),
    ("Camila", "Martínez", "41222999"), ("Mateo", "Sánchez", "39444111"),
    ("Julieta", "Romero", "37666333"), ("Nicolás", "Torres", "34888222"),
    ("Agustina", "Álvarez", "43111777"), ("Facundo", "Ruiz", "32999555"),
    ("Florencia", "Herrera", "40777444"), ("Bruno", "Castro", "38222111"),
    ("Paula", "Medina", "36444555"), ("Ignacio", "Aguirre", "35666777"),
    ("Milagros", "Benítez", "44111333"), ("Santiago", "Quiroga", "37222444"),
    ("Rocío", "Molina", "41888555"), ("Lautaro", "Giménez", "39333666"),
    ("Antonella", "Ríos", "42555888"), ("Franco", "Acosta", "33444999"),
    ("Micaela", "Sosa", "40999111"), ("Emiliano", "Ortiz", "38777222"),
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
        self.generos = {l[0]: l[5] for l in LIBROS}
        generos = sorted(set(self.generos.values()))
        self.preferencia = {s: self.rnd.choice(generos)
                            for s in self.socios_ids}

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
        socio_id = self.rnd.choice(self.socios_ids)
        # Cada socio prefiere un género: 70 % de sus pedidos van por ahí.
        preferidos = [e for e in disponibles
                      if self.generos[e.isbn] == self.preferencia[socio_id]]
        if preferidos and self.rnd.random() < 0.7:
            disponibles = preferidos
        ejemplar = self.rnd.choice(disponibles)
        destino = ejemplar.sede_id
        if interbibliotecario:
            destino = self.rnd.choice(
                [s for s in self.sedes_activas if s != ejemplar.sede_id])
        self.intentar(self.prestamos.solicitar, socio_id, ejemplar.id,
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
