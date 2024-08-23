"""
Inventarios Equipos, tareas en el fondo
"""

import logging
from datetime import datetime
from pathlib import Path

import pytz
from openpyxl import Workbook

from config.settings import get_settings
from lib.exceptions import (
    MyAnyError,
    MyBucketNotFoundError,
    MyEmptyError,
    MyFileNotAllowedError,
    MyFileNotFoundError,
    MyIsDeletedError,
    MyNotExistsError,
    MyUploadError,
)
from lib.google_cloud_storage import upload_file_to_gcs
from lib.tasks import set_task_error, set_task_progress
from hercules.app import create_app
from hercules.blueprints.inv_custodias.models import InvCustodia
from hercules.extensions import database

GCS_BASE_DIRECTORY = "inv_custodias"
LOCAL_BASE_DIRECTORY = "exports/inv_custodias"
TIMEZONE = "America/Mexico_City"

bitacora = logging.getLogger(__name__)
bitacora.setLevel(logging.INFO)
formato = logging.Formatter("%(asctime)s:%(levelname)s:%(message)s")
empunadura = logging.FileHandler("logs/inv_custodias.log")
empunadura.setFormatter(formato)
bitacora.addHandler(empunadura)

app = create_app()
app.app_context().push()
database.app = app


def actualizar(tipo: str = None):
    """Actualizar informacion de las custodias"""
    bitacora.info("Inicia crear reporte de custodias XLSX")

    # Entregar mensaje de termino, el nombre del archivo XLSX y la URL publica
    mensaje_termino = ""
    nombre_archivo_xlsx = ""
    public_url = ""
    return mensaje_termino, nombre_archivo_xlsx, public_url


def lanzar_actualizar(tipo: str = None):
    """Lanzar tarea para actualizar informacion de las custodias"""

    # Iniciar la tarea en el fondo
    set_task_progress(0, "Inicia actualizar informacion de las custodias")

    # Ejecutar el creador
    try:
        mensaje_termino, nombre_archivo_xlsx, public_url = actualizar(tipo)
    except MyAnyError as error:
        mensaje_error = str(error)
        set_task_error(mensaje_error)
        return mensaje_error

    # Terminar la tarea en el fondo y entregar el mensaje de termino
    set_task_progress(100, mensaje_termino, nombre_archivo_xlsx, public_url)
    return mensaje_termino


def crear_reporte_xlsx(domicilio_id: int = None):
    """Crear reporte de custodias XLSX"""
    bitacora.info("Inicia crear reporte de custodias XLSX")

    # Entregar mensaje de termino, el nombre del archivo XLSX y la URL publica
    mensaje_termino = ""
    nombre_archivo_xlsx = ""
    public_url = ""
    return mensaje_termino, nombre_archivo_xlsx, public_url


def lanzar_crear_reporte_xlsx(domicilio_id: int = None):
    """Lanzar tarea para crear reporte de custodias XLSX"""

    # Iniciar la tarea en el fondo
    set_task_progress(0, "Inicia crear reporte de custodias XLSX")

    # Ejecutar el creador
    try:
        mensaje_termino, nombre_archivo_xlsx, public_url = crear_reporte_xlsx(domicilio_id)
    except MyAnyError as error:
        mensaje_error = str(error)
        set_task_error(mensaje_error)
        return mensaje_error

    # Terminar la tarea en el fondo y entregar el mensaje de termino
    set_task_progress(100, mensaje_termino, nombre_archivo_xlsx, public_url)
    return mensaje_termino
