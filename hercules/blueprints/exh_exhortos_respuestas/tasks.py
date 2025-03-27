"""
Exh Exhortos Respuestas, tareas en el fondo
"""

from hercules.app import create_app
from hercules.blueprints.exh_exhortos_respuestas.communications.send import enviar_respuesta
from hercules.blueprints.exh_exhortos_respuestas.models import ExhExhortoRespuesta
from hercules.extensions import database
from lib.exceptions import MyAnyError
from lib.tasks import set_task_error, set_task_progress

app = create_app()
app.app_context().push()
database.app = app


def task_enviar_respuesta(exh_exhorto_respuesta_id: int) -> str:
    """Lanzar tarea en el fondo para enviar una respuesta"""
    # Iniciar la tarea en el fondo
    set_task_progress(0, "Se ha lanzado la tarea en el fondo para enviar una respuesta")

    # Ejecutar
    try:
        mensaje_termino, _, _ = enviar_respuesta(exh_exhorto_respuesta_id)
    except MyAnyError as error:
        # Consultar la respuesta para cambiar su estado a RECHAZADO
        exh_exhorto_respuesta = ExhExhortoRespuesta.query.get(exh_exhorto_respuesta_id)
        if exh_exhorto_respuesta is not None:
            exh_exhorto_respuesta.estado = "RECHAZADO"
            exh_exhorto_respuesta.save()
        # Mandar mensaje de error al usuario
        mensaje_error = str(error)
        set_task_error(mensaje_error)
        return mensaje_error

    # Terminar la tarea en el fondo
    set_task_progress(100, mensaje_termino)

    # Entregar mensaje de termino
    return mensaje_termino
