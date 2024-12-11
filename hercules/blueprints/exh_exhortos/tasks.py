"""
Exh Exhortos, tareas en el fondo
"""

from hercules.blueprints.exh_exhortos.tasks.tasks_02_enviar_exhorto import enviar
from hercules.blueprints.exh_exhortos.tasks.tasks_04_consultar_exhorto import consultar
from lib.exceptions import MyAnyError
from lib.tasks import set_task_error, set_task_progress

CANTIDAD_MAXIMA_INTENTOS = 3
SEGUNDOS_ESPERA_ENTRE_INTENTOS = 60  # 1 minuto
TIMEOUT = 30  # 30 segundos


def lanzar_consultar(exh_exhorto_id):
    """Lanzar tarea en el fondo para consultar exhortos"""

    # Iniciar la tarea en el fondo
    set_task_progress(0, "Se ha lanzado exh_exhortos.consultar")

    # Ejecutar
    try:
        mensaje_termino, nombre_archivo, url_publica = consultar(exh_exhorto_id)
    except MyAnyError as error:
        mensaje_error = str(error)
        set_task_error(mensaje_error)
        return mensaje_error

    # Terminar la tarea en el fondo
    set_task_progress(100, mensaje_termino, nombre_archivo, url_publica)

    # Entregar mensaje de termino
    return mensaje_termino


def lanzar_enviar(exhorto_origen_id: str):
    """Lanzar tarea en el fondo para enviar exhortos"""

    # Iniciar la tarea en el fondo
    set_task_progress(0, "Se ha lanzado exh_exhortos.enviar")

    # Ejecutar
    try:
        mensaje_termino, nombre_archivo, url_publica = enviar(exhorto_origen_id)
    except MyAnyError as error:
        mensaje_error = str(error)
        set_task_error(mensaje_error)
        return mensaje_error

    # Terminar la tarea en el fondo
    set_task_progress(100, mensaje_termino, nombre_archivo, url_publica)

    # Entregar mensaje de termino
    return mensaje_termino
