"""
Exh Exhortos Actualizaciones, tareas en el fondo
"""

from hercules.app import create_app
from hercules.blueprints.exh_exhortos_actualizaciones.communications.send import enviar_actualizacion
from hercules.extensions import database
from lib.exceptions import MyAnyError
from lib.tasks import set_task_error, set_task_progress

app = create_app()
app.app_context().push()
database.app = app


def task_enviar_actualizacion(exh_exhorto_actualizacion_id: int) -> str:
    """Lanzar tarea en el fondo para enviar una actualización"""
    # Iniciar la tarea en el fondo
    set_task_progress(0, "Se ha lanzado la tarea en el fondo para enviar una actualización")

    # Ejecutar
    try:
        mensaje_termino, nombre_archivo, url_publica = enviar_actualizacion(exh_exhorto_actualizacion_id)
    except MyAnyError as error:
        mensaje_error = str(error)
        set_task_error(mensaje_error)
        return mensaje_error

    # Terminar la tarea en el fondo
    set_task_progress(100, mensaje_termino, nombre_archivo, url_publica)

    # Entregar mensaje de termino
    return mensaje_termino
