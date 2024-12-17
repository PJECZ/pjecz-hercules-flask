"""
Exh Exhortos, tareas en el fondo
"""

from hercules.blueprints.exh_exhortos.tasks.tasks_02_enviar_exhorto import task_enviar_exhorto
from hercules.blueprints.exh_exhortos.tasks.tasks_04_consultar_exhorto import task_consultar_exhorto
from hercules.blueprints.exh_exhortos.tasks.tasks_05_responder_exhorto import task_responder_exhorto
from hercules.blueprints.exh_exhortos.tasks.tasks_06_enviar_actualizacion import task_enviar_actualizacion
from hercules.blueprints.exh_exhortos.tasks.tasks_07_enviar_promocion import task_enviar_promocion
from lib.exceptions import MyAnyError
from lib.tasks import set_task_error, set_task_progress


def lanzar_task_02_enviar_exhorto(exhorto_origen_id: str) -> str:
    """Lanzar tarea en el fondo para enviar un exhorto"""
    # Iniciar la tarea en el fondo
    set_task_progress(0, "Se ha lanzado la tarea en el fondo para enviar un exhorto")

    # Ejecutar
    try:
        mensaje_termino, nombre_archivo, url_publica = task_enviar_exhorto(exhorto_origen_id)
    except MyAnyError as error:
        mensaje_error = str(error)
        set_task_error(mensaje_error)
        return mensaje_error

    # Terminar la tarea en el fondo
    set_task_progress(100, mensaje_termino, nombre_archivo, url_publica)

    # Entregar mensaje de termino
    return mensaje_termino


def lanzar_task_04_consultar_exhorto(folio_seguimiento: str) -> str:
    """Lanzar tarea en el fondo para consultar un exhorto"""
    # Iniciar la tarea en el fondo
    set_task_progress(0, "Se ha lanzado la tarea en el fondo para consultar un exhorto")

    # Ejecutar
    try:
        mensaje_termino, nombre_archivo, url_publica = task_consultar_exhorto(folio_seguimiento)
    except MyAnyError as error:
        mensaje_error = str(error)
        set_task_error(mensaje_error)
        return mensaje_error

    # Terminar la tarea en el fondo
    set_task_progress(100, mensaje_termino, nombre_archivo, url_publica)

    # Entregar mensaje de termino
    return mensaje_termino


def lanzar_task_05_responder_exhorto(folio_seguimiento: str) -> str:
    """Lanzar tarea en el fondo para responder un exhorto"""
    # Iniciar la tarea en el fondo
    set_task_progress(0, "Se ha lanzado la tarea en el fondo para responder un exhorto")

    # Ejecutar
    try:
        mensaje_termino, nombre_archivo, url_publica = task_responder_exhorto(folio_seguimiento)
    except MyAnyError as error:
        mensaje_error = str(error)
        set_task_error(mensaje_error)
        return mensaje_error

    # Terminar la tarea en el fondo
    set_task_progress(100, mensaje_termino, nombre_archivo, url_publica)

    # Entregar mensaje de termino
    return mensaje_termino


def lanzar_task_06_enviar_actualizacion(exhorto_origen_id: str) -> str:
    """Lanzar tarea en el fondo para enviar una actualización"""
    # Iniciar la tarea en el fondo
    set_task_progress(0, "Se ha lanzado la tarea en el fondo para enviar una actualización")

    # Ejecutar
    try:
        mensaje_termino, nombre_archivo, url_publica = task_enviar_actualizacion(exhorto_origen_id)
    except MyAnyError as error:
        mensaje_error = str(error)
        set_task_error(mensaje_error)
        return mensaje_error

    # Terminar la tarea en el fondo
    set_task_progress(100, mensaje_termino, nombre_archivo, url_publica)

    # Entregar mensaje de termino
    return mensaje_termino


def lanzar_task_07_enviar_promocion(exhorto_origen_id: str) -> str:
    """Lanzar tarea en el fondo para enviar una promoción"""
    # Iniciar la tarea en el fondo
    set_task_progress(0, "Se ha lanzado la tarea en el fondo para enviar una promoción")

    # Ejecutar
    try:
        mensaje_termino, nombre_archivo, url_publica = task_enviar_promocion(exhorto_origen_id)
    except MyAnyError as error:
        mensaje_error = str(error)
        set_task_error(mensaje_error)
        return mensaje_error

    # Terminar la tarea en el fondo
    set_task_progress(100, mensaje_termino, nombre_archivo, url_publica)

    # Entregar mensaje de termino
    return mensaje_termino
