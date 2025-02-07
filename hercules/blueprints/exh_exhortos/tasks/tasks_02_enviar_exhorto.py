"""
Tareas en el fondo, Exh Exhortos 02 Enviar Exhorto
"""

import time
from datetime import datetime

import requests

from hercules.app import create_app
from hercules.blueprints.estados.models import Estado
from hercules.blueprints.exh_exhortos.models import ExhExhorto
from hercules.blueprints.exh_exhortos.tasks.tasks_00_bitacora import bitacora
from hercules.blueprints.exh_externos.models import ExhExterno
from hercules.blueprints.municipios.models import Municipio
from hercules.extensions import database
from lib.exceptions import (
    MyAnyError,
    MyBucketNotFoundError,
    MyConnectionError,
    MyFileNotFoundError,
    MyNotExistsError,
    MyNotValidParamError,
)
from lib.google_cloud_storage import get_blob_name_from_url, get_file_from_gcs

app = create_app()
app.app_context().push()
database.app = app

CANTIDAD_MAXIMA_INTENTOS = 3
SEGUNDOS_ESPERA_ENTRE_INTENTOS = 60  # 1 minuto
TIMEOUT = 30  # 30 segundos


def task_enviar_exhorto(exhorto_origen_id: str = "") -> tuple[str, str, str]:
    """Enviar exhorto"""
    bitacora.info("Inicia enviar exhorto")

    # Consultar el exhorto con exhorto_origen_id
    exh_exhorto = ExhExhorto.query.filter_by(exhorto_origen_id=exhorto_origen_id).filter_by(estatus="A").first()

    # Validar que exista el exhorto
    if exh_exhorto is None:
        mensaje_advertencia = f"No existe el exhorto con ID {exhorto_origen_id}"
        bitacora.error(mensaje_advertencia)
        raise MyNotExistsError(mensaje_advertencia)

    # Validar que su estado sea POR ENVIAR
    if exh_exhorto.estado != "POR ENVIAR":
        mensaje_advertencia = f"El exhorto con ID {exhorto_origen_id} no está en estado POR ENVIAR"
        bitacora.error(mensaje_advertencia)
        raise MyNotExistsError(mensaje_advertencia)

    # Obtener el tiempo actual
    tiempo_actual = datetime.now()

    # Informar a la bitácora que se va a enviar el exhorto
    mensaje = f"Enviando el exhorto {exh_exhorto.exhorto_origen_id}..."
    bitacora.info(mensaje)

    # Consultar el Estado de destino a partir del ID del Municipio en municipio_destino_id
    municipio = Municipio.query.get(exh_exhorto.municipio_destino_id)
    if municipio is None:
        mensaje_advertencia = f"No existe el municipio con ID {exh_exhorto.municipio_destino_id}"
        bitacora.error(mensaje_advertencia)
        raise MyNotExistsError(mensaje_advertencia)
    estado = Estado.query.get(municipio.estado_id)
    if estado is None:
        mensaje_advertencia = f"No existe el estado con ID {municipio.estado_id}"
        bitacora.error(mensaje_advertencia)
        raise MyNotExistsError(mensaje_advertencia)

    # Consultar el ExhExterno con el ID del Estado, tomar el primero porque solo debe haber uno
    exh_externo = ExhExterno.query.filter_by(estado_id=estado.id).first()
    if exh_externo is None:
        mensaje_advertencia = f"No hay datos en exh_externos del estado {estado.nombre}"
        bitacora.error(mensaje_advertencia)
        raise MyNotExistsError(mensaje_advertencia)

    # Si exh_externo no tiene API-key
    if exh_externo.api_key is None or exh_externo.api_key == "":
        mensaje_advertencia = f"No tiene API-key en exh_externos el estado {estado.nombre}"
        bitacora.error(mensaje_advertencia)
        raise MyNotExistsError(mensaje_advertencia)

    # Si exh_externo no tiene endpoint para enviar exhortos
    if exh_externo.endpoint_recibir_exhorto is None or exh_externo.endpoint_recibir_exhorto == "":
        mensaje_advertencia = f"No tiene endpoint para enviar exhortos el estado {estado.nombre}"
        bitacora.error(mensaje_advertencia)
        raise MyNotExistsError(mensaje_advertencia)

    # Si exh_externo no tiene endpoint para enviar archivos
    if exh_externo.endpoint_recibir_exhorto_archivo is None or exh_externo.endpoint_recibir_exhorto_archivo == "":
        mensaje_advertencia = f"No tiene endpoint para enviar archivos el estado {estado.nombre}"
        bitacora.error(mensaje_advertencia)
        raise MyNotExistsError(mensaje_advertencia)

    # Consultar el municipio de municipio_destino_id para enviar su clave INEGI
    municipio_destino = Municipio.query.get(exh_exhorto.municipio_destino_id)
    if municipio_destino is None:
        mensaje_advertencia = f"No existe municipio_destino_id {exh_exhorto.municipio_destino_id}"
        bitacora.error(mensaje_advertencia)
        raise MyNotExistsError(mensaje_advertencia)

    # Bucle para juntar los datos de las partes
    partes = []
    for exh_exhorto_parte in exh_exhorto.exh_exhortos_partes:
        partes.append(
            {
                "nombre": str(exh_exhorto_parte.nombre),
                "apellidoPaterno": str(exh_exhorto_parte.apellido_paterno),
                "apellidoMaterno": str(exh_exhorto_parte.apellido_materno),
                "genero": str(exh_exhorto_parte.genero),
                "esPersonaMoral": bool(exh_exhorto_parte.es_persona_moral),
                "tipoParte": int(exh_exhorto_parte.tipo_parte),
                "tipoParteNombre": str(exh_exhorto_parte.tipo_parte_nombre),
            }
        )

    # Bucle para juntar los datos de los archivos exh_exhortos_archivos
    archivos = []
    for exh_exhorto_archivo in exh_exhorto.exh_exhortos_archivos:
        archivos.append(
            {
                "nombreArchivo": str(exh_exhorto_archivo.nombre_archivo),
                "hashSha1": str(exh_exhorto_archivo.hash_sha1),
                "hashSha256": str(exh_exhorto_archivo.hash_sha256),
                "tipoDocumento": int(exh_exhorto_archivo.tipo_documento),
            }
        )

    # Definir los datos del exhorto
    datos_exhorto = {
        "exhortoOrigenId": str(exh_exhorto.exhorto_origen_id),
        "municipioDestinoId": int(municipio_destino.clave),
        "materiaClave": str(exh_exhorto.materia_clave),
        "estadoOrigenId": int(exh_exhorto.municipio_origen.estado.clave),
        "municipioOrigenId": int(exh_exhorto.municipio_origen.clave),
        "juzgadoOrigenId": str(exh_exhorto.juzgado_origen_id),
        "juzgadoOrigenNombre": str(exh_exhorto.juzgado_origen_nombre),
        "numeroExpedienteOrigen": str(exh_exhorto.numero_expediente_origen),
        "numeroOficioOrigen": str(exh_exhorto.numero_oficio_origen),
        "tipoJuicioAsuntoDelitos": str(exh_exhorto.tipo_juicio_asunto_delitos),
        "juezExhortante": str(exh_exhorto.juez_exhortante),
        "partes": partes,
        "fojas": int(exh_exhorto.fojas),
        "diasResponder": int(exh_exhorto.dias_responder),
        "tipoDiligenciacionNombre": str(exh_exhorto.tipo_diligenciacion_nombre),
        "fechaOrigen": exh_exhorto.fecha_origen.strftime("%Y-%m-%d %H:%M:%S"),
        "observaciones": str(exh_exhorto.observaciones),
        "archivos": archivos,
    }

    # Enviar el exhorto (ETAPA 2)
    contenido = None
    mensaje_advertencia = ""
    try:
        respuesta = requests.post(
            exh_externo.endpoint_recibir_exhorto,
            headers={"X-Api-Key": exh_externo.api_key},
            timeout=TIMEOUT,
            json=datos_exhorto,
        )
        respuesta.raise_for_status()
        contenido = respuesta.json()
    except requests.exceptions.ConnectionError:
        mensaje_advertencia = "No hubo respuesta del servidor al enviar el exhorto"
    except requests.exceptions.HTTPError as error:
        mensaje_advertencia = f"Status Code {str(error)} al enviar el exhorto"
    except requests.exceptions.RequestException:
        mensaje_advertencia = "Falla desconocida al enviar el exhorto"

    # Si hubo mensaje_advertencia por problemas de comunicación
    if mensaje_advertencia != "":
        bitacora.warning(mensaje_advertencia)
        raise MyConnectionError(mensaje_advertencia)

    # Validar el contenido de la respuesta
    if not ("success", "message", "errors", "data") in contenido:
        mensaje_advertencia = "Falla la validación de success, message, errors y data"
        bitacora.warning(mensaje_advertencia)
        raise MyConnectionError(mensaje_advertencia)

    # Si success es FALSO, mandar a la bitácora el listado de errores y terminar
    if contenido["success"] is False:
        bitacora.warning(",".join(contenido["errors"]))
        raise MyAnyError("El envío del exhorto no fue exitoso. Ver errores en bitácora.")

    # Mandar los archivos del exhorto con multipart/form-data (ETAPA 3)
    data = None
    for exh_exhorto_archivo in exh_exhorto.exh_exhortos_archivos:
        # Informar al bitácora que se va a enviar el archivo
        bitacora.info(f"Enviando archivo {exh_exhorto_archivo.nombre_archivo}...")
        # Pausa de 2 segundos entre envios de archivos
        time.sleep(2)
        # Obtener el contenido del archivo desde GCStorage
        try:
            archivo_contenido = get_file_from_gcs(
                bucket_name=app.config["CLOUD_STORAGE_DEPOSITO"],
                blob_name=get_blob_name_from_url(exh_exhorto_archivo.url),
            )
        except (MyBucketNotFoundError, MyFileNotFoundError, MyNotValidParamError) as error:
            mensaje_error = f"Falla al tratar de bajar el archivo del storage {str(error)}"
            bitacora.error(mensaje_error)
            raise MyFileNotFoundError(mensaje_error)
        # Enviar el archivo
        contenido = None
        mensaje_advertencia = ""
        try:
            respuesta = requests.post(
                url=exh_externo.endpoint_recibir_exhorto_archivo,
                headers={"X-Api-Key": exh_externo.api_key},
                timeout=TIMEOUT,
                data={"exhortoOrigenId": exh_exhorto.exhorto_origen_id},
                files={"archivo": (exh_exhorto_archivo.nombre_archivo, archivo_contenido, "application/pdf")},
            )
            respuesta.raise_for_status()
            contenido = respuesta.json()
        except requests.exceptions.ConnectionError:
            mensaje_advertencia = "No hubo respuesta del servidor al enviar el archivo"
        except requests.exceptions.HTTPError as error:
            mensaje_advertencia = f"Status Code {str(error)} al enviar el archivo"
        except requests.exceptions.RequestException:
            mensaje_advertencia = "Falla desconocida al enviar el archivo"
        # Si hubo mensaje_advertencia por problemas de comunicación
        if mensaje_advertencia != "":
            bitacora.warning(mensaje_advertencia)
            raise MyAnyError(mensaje_advertencia)
        # Validar el contenido de la respuesta
        if not ("success", "message", "errors", "data") in contenido:
            mensaje_advertencia = "Falla la validación de success, message, errors y data"
            bitacora.warning(mensaje_advertencia)
            raise MyConnectionError(mensaje_advertencia)
        # Si success es FALSO, mandar a la bitácora el listado de errores y terminar
        if contenido["success"] is False:
            bitacora.warning(",".join(contenido["errors"]))
            raise MyAnyError("El envío del archivo no fue exitoso. Ver errores en bitácora.")
        # Tomar el data que llega por enviar el archivo
        data = contenido["data"]

    # Validar que el ULTIMO acuse tenga en el data
    mensaje_advertencia = ""
    if "acuse" not in data:
        mensaje_advertencia = "Cambio el estado a RECHAZADO porque la respuesta no tiene 'acuse'"
        bitacora.warning(mensaje_advertencia)
    acuse = data["acuse"]

    # Validar que el acuse tenga "exhortoOrigenId"
    try:
        acuse_exhorto_origen_id = str(acuse["exhortoOrigenId"])
        bitacora.info("Acuse exhortoOrigenId: %s", acuse_exhorto_origen_id)
    except KeyError:
        mensaje_advertencia = "Faltó exhortoOrigenId en el acuse"
        bitacora.warning(mensaje_advertencia)

    # Validar que en acuse tenga "folioSeguimiento"
    try:
        acuse_folio_seguimiento = str(acuse["folioSeguimiento"])
        bitacora.info("Acuse folioSeguimiento: %s", acuse_folio_seguimiento)
    except KeyError:
        mensaje_advertencia = "Faltó folioSeguimiento en el acuse"
        bitacora.warning(mensaje_advertencia)

    # Validar que en acuse tenga "fechaHoraRecepcion"
    try:
        acuse_fecha_hora_recepcion_str = str(acuse["fechaHoraRecepcion"])
        acuse_fecha_hora_recepcion = datetime.strptime(acuse_fecha_hora_recepcion_str, "%Y-%m-%d %H:%M:%S")
        bitacora.info("Acuse fechaHoraRecepcion: %s", acuse_fecha_hora_recepcion_str)
    except (KeyError, ValueError):
        mensaje_advertencia = "Faltó o es incorrecta fechaHoraRecepcion en el acuse"
        bitacora.warning(mensaje_advertencia)

    # Puede venir "municipioAreaRecibeId" en acuse porque es opcional
    acuse_municipio_area_recibe_id = None
    try:
        acuse_municipio_area_recibe_id = int(acuse["municipioAreaRecibeId"])
        bitacora.info("Acuse municipioAreaRecibeId: %s", acuse_municipio_area_recibe_id)
    except (KeyError, ValueError):
        pass

    # Puede venir "areaRecibeId" en acuse porque es opcional
    acuse_area_recibe_id = None
    try:
        acuse_area_recibe_id = str(acuse["areaRecibeId"])
        bitacora.info("Acuse areaRecibeId: %s", acuse_area_recibe_id)
    except KeyError:
        pass

    # Puede venir "areaRecibeNombre" en acuse porque es opcional
    acuse_area_recibe_nombre = None
    try:
        acuse_area_recibe_nombre = str(acuse["areaRecibeNombre"])
        bitacora.info("Acuse areaRecibeNombre: %s", acuse_area_recibe_nombre)
    except KeyError:
        pass

    # Puede venir "urlInfo" en acuse porque es opcional
    acuse_url_info = None
    try:
        acuse_url_info = str(acuse["urlInfo"])
        bitacora.info("Acuse urlInfo: %s", acuse_url_info)
    except KeyError:
        pass

    # Si hubo mensaje_advertencia
    if mensaje_advertencia != "":
        # Actualizar el exhorto, cambiar el estado a RECHAZADO
        exh_exhorto.estado = "RECHAZADO"
        exh_exhorto.save()
    else:
        # Actualizar el exhorto, cambiar el estado a RECIBIDO CON EXITO
        exh_exhorto.estado = "RECIBIDO CON EXITO"
        exh_exhorto.folio_seguimiento = acuse_folio_seguimiento
        exh_exhorto.acuse_fecha_hora_recepcion = acuse_fecha_hora_recepcion
        exh_exhorto.acuse_municipio_area_recibe_id = acuse_municipio_area_recibe_id
        exh_exhorto.acuse_area_recibe_id = acuse_area_recibe_id
        exh_exhorto.acuse_area_recibe_nombre = acuse_area_recibe_nombre
        exh_exhorto.acuse_url_info = acuse_url_info
        exh_exhorto.save()

    # Elaborar mensaje final
    mensaje_termino = f"El exhorto {exhorto_origen_id} se envió con éxito."
    bitacora.info(mensaje_termino)

    # Entregar mensaje_termino, nombre_archivo y url_publica
    return mensaje_termino, "", ""
