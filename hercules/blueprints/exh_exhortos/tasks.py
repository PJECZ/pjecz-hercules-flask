"""
Exh Exhortos, tareas en el fondo
"""

from hercules.blueprints.exh_exhortos.communications.query import consultar_exhorto
from hercules.blueprints.exh_exhortos.communications.reply import responder_exhorto
from hercules.blueprints.exh_exhortos.communications.send import enviar_exhorto
from lib.exceptions import MyAnyError
from lib.tasks import set_task_error, set_task_progress


def task_enviar_exhorto(exhorto_origen_id: str) -> str:
    """Lanzar tarea en el fondo para enviar un exhorto"""
    # Iniciar la tarea en el fondo
    set_task_progress(0, "Se ha lanzado la tarea en el fondo para enviar un exhorto")

    # Ejecutar
    try:
        mensaje_termino, nombre_archivo, url_publica = enviar_exhorto(exhorto_origen_id)
    except MyAnyError as error:
        mensaje_error = str(error)
        set_task_error(mensaje_error)
        return mensaje_error

    # Terminar la tarea en el fondo
    set_task_progress(100, mensaje_termino, nombre_archivo, url_publica)

    # Entregar mensaje de termino
    return mensaje_termino


def task_consultar_exhorto(folio_seguimiento: str) -> str:
    """Lanzar tarea en el fondo para consultar un exhorto"""
    # Iniciar la tarea en el fondo
    set_task_progress(0, "Se ha lanzado la tarea en el fondo para consultar un exhorto")

    # Ejecutar
    try:
        mensaje_termino, nombre_archivo, url_publica = consultar_exhorto(folio_seguimiento)
    except MyAnyError as error:
        mensaje_error = str(error)
        set_task_error(mensaje_error)
        return mensaje_error

    # Terminar la tarea en el fondo
    set_task_progress(100, mensaje_termino, nombre_archivo, url_publica)

    # Entregar mensaje de termino
    return mensaje_termino


def task_responder_exhorto(folio_seguimiento: str) -> str:
    """Lanzar tarea en el fondo para responder un exhorto"""
    # Iniciar la tarea en el fondo
    set_task_progress(0, "Se ha lanzado la tarea en el fondo para responder un exhorto")

    # Ejecutar
    try:
        mensaje_termino, nombre_archivo, url_publica = responder_exhorto(folio_seguimiento)
    except MyAnyError as error:
        mensaje_error = str(error)
        set_task_error(mensaje_error)
        return mensaje_error

    # Terminar la tarea en el fondo
    set_task_progress(100, mensaje_termino, nombre_archivo, url_publica)

    # Entregar mensaje de termino
    return mensaje_termino
