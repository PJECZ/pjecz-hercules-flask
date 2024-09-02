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
    MyUploadError,
)
from lib.google_cloud_storage import upload_file_to_gcs
from lib.safe_string import safe_string
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


def exportar_reporte_xlsx(tipo: str = None):
    """Exportar reporte de equipos XLSX"""
    bitacora.info("Inicia exportar reporte de equipos XLSX")

    # Inicializar la lista de mensajes
    mensajes = []

    # Consultar los equipos con estatus 'A' y del tipo dado
    tipo = safe_string(tipo)
    inv_equipos = InvEquipo.query.filter(InvEquipo.tipo == tipo).filter(InvEquipo.estatus == "A").order_by(InvEquipo.id).all()

    # Iniciar el archivo XLSX
    libro = Workbook()

    # Tomar la hoja del libro XLSX
    hoja = libro.active

    # Agregar la fila con las cabeceras de las columnas
    hoja.append(
        [
            "EQUIPO ID",
            "CUSTODIA ID",
            "EMAIL",
            "NOMBRE COMPLETO",
            "DISTRITO CLAVE",
            "EDIFICIO",
            "OFICINA",
            "MARCA",
            "MODELO",
            "AÑO DE FAB.",
            "RED",
            "DIRECCION IP",
            "MAC ADDRESS",
            "ESTADO",
        ]
    )

    # Inicializar el contador
    contador = 0

    # Bucle por los equipos
    for inv_equipo in inv_equipos:
        hoja.append(
            [
                inv_equipo.id,
                inv_equipo.inv_custodia_id,
                inv_equipo.inv_custodia.usuario.email,
                inv_equipo.inv_custodia.nombre_completo,
                inv_equipo.inv_custodia.usuario.oficina.distrito.clave,
                inv_equipo.inv_custodia.usuario.oficina.domicilio.edificio,
                inv_equipo.inv_custodia.usuario.oficina.clave,
                inv_equipo.inv_modelo.inv_marca.nombre,
                inv_equipo.inv_modelo.descripcion,
                inv_equipo.fecha_fabricacion_anio,
                inv_equipo.inv_red.nombre,
                inv_equipo.direccion_ip,
                inv_equipo.direccion_mac,
                inv_equipo.estado,
            ]
        )
        contador += 1

    # Si el contador es cero, entregar un error
    if contador == 0:
        mensaje_error = f"No hay equipos de tipo {tipo} para exportar."
        bitacora.error(mensaje_error)
        raise MyEmptyError(mensaje_error)

    # Determinar el nombre del archivo XLSX
    tipo_str = tipo.lower().replace(" ", "_")
    ahora = datetime.now(tz=pytz.timezone(TIMEZONE))
    nombre_archivo_xlsx = f"{tipo_str}_{ahora.strftime('%Y-%m-%d_%H%M%S')}.xlsx"

    # Determinar las rutas con directorios con el año y el número de mes en dos digitos
    ruta_local = Path(LOCAL_BASE_DIRECTORY, ahora.strftime("%Y"), ahora.strftime("%m"))
    ruta_gcs = Path(GCS_BASE_DIRECTORY, ahora.strftime("%Y"), ahora.strftime("%m"))

    # Si no existe el directorio local, crearlo
    Path(ruta_local).mkdir(parents=True, exist_ok=True)

    # Guardar el archivo XLSX
    ruta_local_archivo_xlsx = str(Path(ruta_local, nombre_archivo_xlsx))
    libro.save(ruta_local_archivo_xlsx)
    mensaje_guardar_xlsx = f"Se guardo el archivo XLSX en {ruta_local_archivo_xlsx}"
    mensajes.append(mensaje_guardar_xlsx)
    bitacora.info(mensaje_guardar_xlsx)

    # Si esta configurado Google Cloud Storage
    settings = get_settings()
    if settings.CLOUD_STORAGE_DEPOSITO != "":
        # Leer el contenido del archivo XLSX
        with open(ruta_local_archivo_xlsx, "rb") as archivo:
            # Subir el archivo XLSX a Google Cloud Storage
            try:
                public_url = upload_file_to_gcs(
                    bucket_name=settings.CLOUD_STORAGE_DEPOSITO,
                    blob_name=f"{ruta_gcs}/{nombre_archivo_xlsx}",
                    content_type="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
                    data=archivo.read(),
                )
                mensaje_gcs = f"Se subio el archivo XLSX a GCS {public_url}"
                mensajes.append(mensaje_gcs)
                bitacora.info(mensaje_gcs)
            except (MyEmptyError, MyBucketNotFoundError, MyFileNotAllowedError, MyFileNotFoundError, MyUploadError) as error:
                mensaje_fallo_gcs = str(error)
                mensajes.append(mensaje_fallo_gcs)
                bitacora.warning("Falló al subir el archivo XLSX a GCS: %s", mensaje_fallo_gcs)

    # Entregar mensaje de termino, el nombre del archivo XLSX y la URL publica
    mensaje_final = f"Se exportaron {contador} equipos a {nombre_archivo_xlsx}"
    mensajes.append(mensaje_final)
    bitacora.info(mensaje_final)
    return "\n".join(mensajes), nombre_archivo_xlsx, public_url


def lanzar_exportar_reporte_xlsx(tipo: str = None):
    """Lanzar tarea para exportar reporte de equipos XLSX"""

    # Iniciar la tarea en el fondo
    set_task_progress(0, "Inicia exportar reporte de equipos XLSX")

    # Ejecutar el creador
    try:
        mensaje_termino, nombre_archivo_xlsx, public_url = exportar_reporte_xlsx(tipo)
    except MyAnyError as error:
        mensaje_error = str(error)
        set_task_error(mensaje_error)
        return mensaje_error

    # Terminar la tarea en el fondo y entregar el mensaje de termino
    set_task_progress(100, mensaje_termino, nombre_archivo_xlsx, public_url)
    return mensaje_termino
