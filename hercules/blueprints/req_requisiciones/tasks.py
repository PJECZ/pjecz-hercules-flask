"""
Requisiciones, tareas en el fondo
"""
from datetime import datetime
import json
import logging
import os

import requests
from lib.exceptions import (
    MyAnyError,
    MyConnectionError,
    MyMissingConfigurationError,
    MyNotValidParamError,
    MyStatusCodeError,
    MyRequestError,
    MyResponseError,
)
from lib.safe_string import safe_string


from hercules.app import create_app
from hercules.blueprints.req_requisiciones.models import ReqRequisicion
from hercules.blueprints.usuarios.models import Usuario
from hercules.blueprints.req_requisiciones.conversions.convert_to_pdf import convertir_a_pdf
from lib.tasks import set_task_error, set_task_progress



def lanzar_convertir_requisicion_a_pdf(req_requisicion_id: str) -> str:
    """Lanzar tarea en el fondo para convertir a PDF"""
    # Iniciar la tarea en el fondo
    set_task_progress(0, "Se ha lanzado la tarea en el fondo para convertir a PDF")

    # Ejecutar
    try:
        mensaje_termino, _, _ = convertir_a_pdf(req_requisicion_id)
    except MyAnyError as error:
        # Mandar mensaje de error al usuario
        mensaje_error = str(error)
        set_task_error(mensaje_error)
        return mensaje_error

    # Terminar la tarea en el fondo
    set_task_progress(100, mensaje_termino)

    # Entregar mensaje de termino
    return mensaje_termino
