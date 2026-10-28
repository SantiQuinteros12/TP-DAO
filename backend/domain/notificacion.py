"""Entidad Notificacion (proceso opcional: envío de notificaciones)."""


class Notificacion:
    """Mensaje dirigido a un socio, generado por eventos del dominio."""

    def __init__(self, socio_id, mensaje, fecha_hora, leida=False, id=None):
        self.id = id
        self.socio_id = socio_id
        self.mensaje = mensaje
        self.fecha_hora = fecha_hora
        self.leida = leida

    def marcar_leida(self):
        self.leida = True
