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
from hercules.blueprints.inv_equipos.models import InvEquipo
from hercules.extensions import database

GCS_BASE_DIRECTORY = "inv_equipos"
LOCAL_BASE_DIRECTORY = "exports/inv_equipos"
TIMEZONE = "America/Mexico_City"

bitacora = logging.getLogger(__name__)
bitacora.setLevel(logging.INFO)
formato = logging.Formatter("%(asctime)s:%(levelname)s:%(message)s")
empunadura = logging.FileHandler("logs/inv_equipos.log")
empunadura.setFormatter(formato)
bitacora.addHandler(empunadura)

app = create_app()
app.app_context().push()
database.app = app


def actualizar(tipo: str = None):
    """Actualizar informacion de los equipos"""
    bitacora.info("Inicia crear reporte de equipos XLSX")

    # Consultar las cantidades de equipos con estatus 'A' por tipo
    consulta = (
        database.session.query(InvEquipo.tipo, database.func.count(InvEquipo.id).label("cantidad"))
        .filter(InvEquipo.estatus == "A")
        .group_by(InvEquipo.tipo)
        .order_by(InvEquipo.tipo)
    )

    # Entregar mensaje de termino, el nombre del archivo XLSX y la URL publica
    mensaje_termino = ""
    nombre_archivo_xlsx = ""
    public_url = ""
    return mensaje_termino, nombre_archivo_xlsx, public_url


def lanzar_actualizar(tipo: str = None):
    """Lanzar tarea para actualizar informacion de los equipos"""

    # Iniciar la tarea en el fondo
    set_task_progress(0, "Inicia actualizar informacion de los equipos")

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


def crear_reporte_xlsx(tipo: str = None):
    """Crear reporte de equipos XLSX"""
    bitacora.info("Inicia crear reporte de equipos XLSX")

    # Entregar mensaje de termino, el nombre del archivo XLSX y la URL publica
    mensaje_termino = ""
    nombre_archivo_xlsx = ""
    public_url = ""
    return mensaje_termino, nombre_archivo_xlsx, public_url


def lanzar_crear_reporte_xlsx(tipo: str = None):
    """Lanzar tarea para crear reporte de equipos XLSX"""

    # Iniciar la tarea en el fondo
    set_task_progress(0, "Inicia crear reporte de equipos XLSX")

    # Ejecutar el creador
    try:
        mensaje_termino, nombre_archivo_xlsx, public_url = crear_reporte_xlsx(tipo)
    except MyAnyError as error:
        mensaje_error = str(error)
        set_task_error(mensaje_error)
        return mensaje_error

    # Terminar la tarea en el fondo y entregar el mensaje de termino
    set_task_progress(100, mensaje_termino, nombre_archivo_xlsx, public_url)
    return mensaje_termino
