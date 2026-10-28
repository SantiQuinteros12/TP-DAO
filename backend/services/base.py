"""Clase base de los servicios de aplicación (casos de uso)."""

from domain.eventos import PublicadorEventos
from domain.excepciones import EntidadNoEncontradaError


class ServicioBase:
    """
    Los servicios orquestan entidades y repositorios; las reglas propias de
    cada entidad viven en el dominio y aquí sólo se validan las que
    requieren consultar otros agregados (duplicados, límites, etc.).

    :param uow: unidad de trabajo con los repositorios
    :param reloj: fuente de fecha/hora (inyectable para tests)
    :param publicador: publicador de eventos de dominio (Observer)
    """

    def __init__(self, uow, reloj, publicador=None):
        self.uow = uow
        self.reloj = reloj
        self.publicador = publicador or PublicadorEventos()

    @staticmethod
    def _requerir(repositorio, id, nombre_entidad):
        entidad = repositorio.obtener(id)
        if entidad is None:
            raise EntidadNoEncontradaError(nombre_entidad, id)
        return entidad

    def _publicar(self, *eventos):
        self.publicador.publicar_todos(eventos, self.uow)

    def _publicar_de(self, entidad):
        self._publicar(*entidad.extraer_eventos())
