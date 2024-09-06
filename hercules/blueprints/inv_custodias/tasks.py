"""
Inventarios Custodias, tareas en el fondo
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
from hercules.blueprints.domicilios.models import Domicilio
from hercules.blueprints.inv_custodias.models import InvCustodia
from hercules.blueprints.oficinas.models import Oficina
from hercules.blueprints.usuarios.models import Usuario
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


def exportar_reporte_xlsx(domicilio_id: int = None):
    """Exportar reporte de custodias XLSX"""
    bitacora.info("Inicia exportar reporte de custodias XLSX")

    # Inicializar la lista de mensajes
    mensajes = []

    # Consultar y validar el domicilio dado
    domicilio = Domicilio.query.get(domicilio_id)
    if domicilio is None:
        raise MyNotExistsError("Domicilio no encontrado")
    if domicilio.estatus != "A":
        raise MyIsDeletedError("Domicilio no activo")

    # Consultar las custodias del domicilio
    inv_custodias = (
        database.session.query(InvCustodia)
        .join(Usuario, Usuario.id == InvCustodia.usuario_id)
        .join(Oficina, Oficina.id == Usuario.oficina_id)
        .join(Domicilio, Domicilio.id == Oficina.domicilio_id)
        .filter(Domicilio.id == domicilio_id)
        .filter(InvCustodia.estatus == "A")
        .order_by(InvCustodia.id)
        .all()
    )

    # Iniciar el archivo XLSX
    libro = Workbook()

    # Tomar la hoja del libro XLSX
    hoja = libro.active

    # Agregar la fila con las cabeceras de las columnas
    hoja.append(
        [
            "CUSTODIA ID",
            "NOMBRE COMPLETO",
            "EMAIL",
            "PUESTO",
            "OFICINA CLAVE",
            "OFICINA DESCIPCION",
            "EDIFICIO",
            "FECHA",
            "C. EQUIPOS",
            "C. FOTOS",
        ]
    )

    # Inicializar el contador
    contador = 0

    # Bucle por las custodias
    for inv_custodia in inv_custodias:
        # Agregar la fila con los datos de la custodia
        hoja.append(
            [
                inv_custodia.id,
                inv_custodia.nombre_completo,
                inv_custodia.usuario.email,
                inv_custodia.usuario.puesto,
                inv_custodia.usuario.oficina.clave,
                inv_custodia.usuario.oficina.descripcion_corta,
                inv_custodia.usuario.oficina.domicilio.edificio,
                inv_custodia.fecha.strftime("%Y-%m-%d"),
                inv_custodia.equipos_cantidad,
                inv_custodia.equipos_fotos_cantidad,
            ]
        )
        contador += 1

    # Si el contador es cero, entregar un error
    if contador == 0:
        mensaje_error = f"No hay equipos en {domicilio.edificio} para exportar."
        bitacora.error(mensaje_error)
        raise MyEmptyError(mensaje_error)

    # Determinar el nombre del archivo XLSX
    edificio_str = domicilio.edificio.lower().replace(" ", "_")
    ahora = datetime.now(tz=pytz.timezone(TIMEZONE))
    nombre_archivo_xlsx = f"{edificio_str}_{ahora.strftime('%Y-%m-%d_%H%M%S')}.xlsx"

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
    mensaje_final = f"Se exportaron {contador} custodias a {nombre_archivo_xlsx}"
    mensajes.append(mensaje_final)
    bitacora.info(mensaje_final)
    return "\n".join(mensajes), nombre_archivo_xlsx, public_url


def lanzar_exportar_reporte_xlsx(domicilio_id: int = None):
    """Lanzar tarea para exportar reporte de custodias XLSX"""

    # Iniciar la tarea en el fondo
    set_task_progress(0, "Inicia exportar reporte de custodias XLSX")

    # Ejecutar el creador
    try:
        mensaje_termino, nombre_archivo_xlsx, public_url = exportar_reporte_xlsx(domicilio_id)
    except MyAnyError as error:
        mensaje_error = str(error)
        set_task_error(mensaje_error)
        return mensaje_error

    # Terminar la tarea en el fondo y entregar el mensaje de termino
    set_task_progress(100, mensaje_termino, nombre_archivo_xlsx, public_url)
    return mensaje_termino
