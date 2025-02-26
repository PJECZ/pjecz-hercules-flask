"""
Communications, Responder Exhorto
"""

import time
from datetime import datetime

import requests

from hercules.app import create_app
from hercules.blueprints.estados.models import Estado
from hercules.blueprints.exh_exhortos.communications import bitacora
from hercules.blueprints.exh_exhortos.models import ExhExhorto
from hercules.blueprints.exh_externos.models import ExhExterno
from hercules.blueprints.municipios.models import Municipio
from hercules.extensions import database
from lib.exceptions import (
    MyAnyError,
    MyBucketNotFoundError,
    MyConnectionError,
    MyFileNotFoundError,
    MyNotExistsError,
    MyNotValidAnswerError,
    MyNotValidParamError,
)
from lib.google_cloud_storage import get_blob_name_from_url, get_file_from_gcs
from lib.pwgen import generar_identificador

app = create_app()
app.app_context().push()
database.app = app

TIMEOUT = 60  # segundos


def responder_exhorto(exh_exhorto_id: int) -> tuple[str, str, str]:
    """Responder exhortos"""
    mensajes = []
    mensaje_info = "Inicia responder exhorto al PJ externo."
    mensajes.append(mensaje_info)
    bitacora.info(mensaje_info)

    # Consultar el exhorto
    exh_exhorto = ExhExhorto.query.get(exh_exhorto_id)

    # Validar que exista el exhorto
    if exh_exhorto is None:
        mensaje_error = f"No existe el exhorto con ID {exh_exhorto_id}"
        bitacora.error(mensaje_error)
        raise MyNotExistsError(mensaje_error)

    # Validar que su estado
    if exh_exhorto.estado not in ("TRANSFERIDO", "PROCESANDO", "DILIGENCIADO"):
        mensaje_error = f"El exhorto con ID {exh_exhorto_id} no tiene el estado TRANSFERIDO, PROCESANDO o DILIGENCIADO"
        bitacora.error(mensaje_error)
        raise MyNotExistsError(mensaje_error)

    # Tomar el estado de ORIGEN a partir de municipio_origen
    municipio = exh_exhorto.municipio_origen  # Es una columna foránea
    estado = municipio.estado

    # Consultar el ExhExterno, tomar el primero porque solo debe haber uno
    exh_externo = ExhExterno.query.filter_by(estado_id=estado.id).first()
    if exh_externo is None:
        mensaje_error = f"No hay datos en exh_externos del estado {estado.nombre}"
        bitacora.error(mensaje_error)
        raise MyNotExistsError(mensaje_error)

    # Si exh_externo no tiene API-key
    if exh_externo.api_key is None or exh_externo.api_key == "":
        mensaje_error = f"No tiene API-key en exh_externos el estado {estado.nombre}"
        bitacora.error(mensaje_error)
        raise MyNotExistsError(mensaje_error)

    # Si exh_externo no tiene endpoint para enviar exhortos
    if exh_externo.endpoint_recibir_respuesta_exhorto is None or exh_externo.endpoint_recibir_respuesta_exhorto == "":
        mensaje_error = f"No tiene endpoint para enviar respuestas el estado {estado.nombre}"
        bitacora.error(mensaje_error)
        raise MyNotExistsError(mensaje_error)

    # Si exh_externo no tiene endpoint para enviar archivos
    if (
        exh_externo.endpoint_recibir_respuesta_exhorto_archivo is None
        or exh_externo.endpoint_recibir_respuesta_exhorto_archivo == ""
    ):
        mensaje_error = f"No tiene endpoint para enviar archivos de respuestas el estado {estado.nombre}"
        bitacora.error(mensaje_error)
        raise MyNotExistsError(mensaje_error)

    # Bucle para juntar los datos de los archivos que SI sean respuesta
    archivos = []
    for archivo in exh_exhorto.exh_exhortos_archivos:
        if archivo.es_respuesta is False:
            continue
        archivos.append(
            {
                "nombreArchivo": str(archivo.nombre_archivo),
                "hashSha1": str(archivo.hash_sha1),
                "hashSha256": str(archivo.hash_sha256),
                "tipoDocumento": int(archivo.tipo_documento),
            }
        )

    # Validar que haya archivos
    if len(archivos) == 0:
        mensaje_error = f"No hay archivos de respuesta en el exhorto con ID {exh_exhorto_id}"
        bitacora.error(mensaje_error)
        raise MyNotExistsError(mensaje_error)

    # Bucle para juntar los datos de los videos
    videos = []
    for video in exh_exhorto.exh_exhortos_videos:
        videos.append(
            {
                "titulo": str(video.titulo),
                "descripcion": str(video.descripcion),
                "fecha": str(video.fecha.strftime("%Y-%m-%d %H:%M:%S")),
                "urlAcceso": str(video.url_acceso),
            }
        )

    # Si no hay videos, entonces definir videos como None
    if len(videos) == 0:
        videos = None

    # Generar identificador para respuesta_origien_id
    respuesta_origen_id = generar_identificador()

    # Definir los datos de la respuesta del exhorto
    payload_for_json = {
        "exhortoId": str(exh_exhorto.exhorto_origen_id),
        "respuestaOrigenId": respuesta_origen_id,
        "municipioTurnadoId": int(exh_exhorto.respuesta_municipio_turnado_id),
        "areaTurnadoId": str(exh_exhorto.respuesta_area_turnado_id),
        "areaTurnadoNombre": str(exh_exhorto.respuesta_area_turnado_nombre),
        "numeroExhorto": str(exh_exhorto.respuesta_numero_exhorto),
        "tipoDiligenciado": int(exh_exhorto.respuesta_tipo_diligenciado),
        "observaciones": str(exh_exhorto.respuesta_observaciones),
        "archivos": archivos,
        "videos": videos,
    }

    # Informar a la bitácora que va a comenzar el envío de la respuesta
    mensaje_info = "Comienza el envío de la respuesta con los siguientes datos:"
    mensajes.append(mensaje_info)
    bitacora.info(mensaje_info)
    for key, value in payload_for_json.items():
        mensaje_info = f"- {key}: {value}"
        mensajes.append(mensaje_info)
        bitacora.info(mensaje_info)

    # Enviar el exhorto
    contenido = None
    mensaje_advertencia = ""
    try:
        respuesta = requests.post(
            url=exh_externo.endpoint_recibir_respuesta_exhorto,
            headers={"X-Api-Key": exh_externo.api_key},
            timeout=TIMEOUT,
            json=payload_for_json,
        )
        respuesta.raise_for_status()
        contenido = respuesta.json()
    except requests.exceptions.ConnectionError:
        mensaje_advertencia = "No hubo respuesta del servidor al enviar la respuesta"
    except requests.exceptions.HTTPError as error:
        mensaje_advertencia = f"Status Code {str(error)} al enviar la respuesta"
    except requests.exceptions.RequestException:
        mensaje_advertencia = "Falla desconocida al enviar la respuesta"

    # Terminar si hubo mensaje_advertencia
    if mensaje_advertencia != "":
        bitacora.warning(mensaje_advertencia)
        raise MyConnectionError(mensaje_advertencia.upper() + "\n" + "\n".join(mensajes))

    # Terminar si NO es correcta estructura de la respuesta
    mensajes_advertencias = []
    if "success" not in contenido or not isinstance(contenido["success"], bool):
        mensajes_advertencias.append("Falta 'success' en la respuesta")
    if "message" not in contenido:
        mensajes_advertencias.append("Falta 'message' en la respuesta")
    if "errors" not in contenido:
        mensajes_advertencias.append("Falta 'errors' en la respuesta")
    if "data" not in contenido:
        mensajes_advertencias.append("Falta 'data' en la respuesta")
    if len(mensajes_advertencias) > 0:
        mensaje_advertencia = ", ".join(mensajes_advertencias)
        bitacora.warning(mensaje_advertencia)
        raise MyNotValidAnswerError(mensaje_advertencia.upper() + "\n" + "\n".join(mensajes))
    if contenido["message"]:
        mensaje_info = f"- message: {contenido['message']}"
        bitacora.info(mensaje_info)
        mensajes.append(mensaje_info)

    # Terminar si success es FALSO
    if contenido["success"] is False:
        mensaje_advertencia = f"Falló el envío de la respuesta porque 'success' es falso: {','.join(contenido['errors'])}"
        bitacora.warning(mensaje_advertencia)
        raise MyNotValidAnswerError(mensaje_advertencia.upper() + "\n" + "\n".join(mensajes))

    # Informar a la bitácora que terminó el envío de la respuesta
    mensaje_info = "Termina el envío de la respuesta."
    mensajes.append(mensaje_info)
    bitacora.info(mensaje_info)

    # Informar a la bitácora que se van a enviar los archivos de la respuesta
    mensaje_info = "Comienza el envío de los archivos de la respuesta."
    mensajes.append(mensaje_info)
    bitacora.info(mensaje_info)

    # Definir los datos que se van a incluir en el envío de los archivos
    payload_for_data = {
        "exhortoOrigenId": str(exh_exhorto.exhorto_origen_id),
        "respuestaOrigenId": str(respuesta_origen_id),
    }
    mensajes_info = f"- exhortoOrigenId: {payload_for_data['exhortoOrigenId']}"
    mensajes.append(mensajes_info)
    bitacora.info(mensajes_info)
    mensajes_info = f"- respuestaOrigenId: {payload_for_data['respuestaOrigenId']}"
    mensajes.append(mensajes_info)
    bitacora.info(mensajes_info)

    # Mandar los archivos de la respuesta con multipart/form-data (ETAPA 3)
    data = None
    for archivo in exh_exhorto.exh_exhortos_archivos:
        # Si el archivo no es respuesta, entonces continuar
        if archivo.es_respuesta is False:
            continue
        # Informar al bitácora que se va a enviar el archivo
        mensaje_info = f"Enviando el archivo {archivo.nombre_archivo}"
        mensajes.append(mensaje_info)
        bitacora.info(mensaje_info)
        # Pausa de 2 segundos entre envios de archivos
        time.sleep(2)
        # Obtener el contenido del archivo desde GCStorage
        try:
            archivo_contenido = get_file_from_gcs(
                bucket_name=app.config["CLOUD_STORAGE_DEPOSITO"],
                blob_name=get_blob_name_from_url(archivo.url),
            )
        except (MyBucketNotFoundError, MyFileNotFoundError, MyNotValidParamError) as error:
            mensaje_error = f"Falla al tratar de bajar el archivo del storage {str(error)}"
            bitacora.error(mensaje_error)
            raise MyFileNotFoundError(mensaje_error.upper() + "\n" + "\n".join(mensajes))
        # Enviar el archivo
        contenido = None
        mensaje_advertencia = ""
        try:
            respuesta = requests.post(
                url=exh_externo.endpoint_recibir_respuesta_exhorto_archivo,
                headers={"X-Api-Key": exh_externo.api_key},
                timeout=TIMEOUT,
                files={"archivo": (archivo.nombre_archivo, archivo_contenido, "application/pdf")},
                data=payload_for_data,
            )
            respuesta.raise_for_status()
            contenido = respuesta.json()
        except requests.exceptions.ConnectionError:
            mensaje_advertencia = "No hubo respuesta del servidor al enviar el archivo de la respuesta"
        except requests.exceptions.HTTPError as error:
            mensaje_advertencia = f"Status Code {str(error)} al enviar el archivo de la respuesta"
        except requests.exceptions.RequestException:
            mensaje_advertencia = "Falla desconocida al enviar el archivo de la respuesta"
        # Terminar si hubo mensaje_advertencia
        if mensaje_advertencia != "":
            bitacora.warning(mensaje_advertencia)
            raise MyAnyError(mensaje_advertencia.upper() + "\n" + "\n".join(mensajes))
        # Terminar si NO es correcta estructura de la respuesta
        mensajes_advertencias = []
        if "success" not in contenido or not isinstance(contenido["success"], bool):
            mensajes_advertencias.append("Falta 'success' en la respuesta")
        if "message" not in contenido:
            mensajes_advertencias.append("Falta 'message' en la respuesta")
        if "errors" not in contenido:
            mensajes_advertencias.append("Falta 'errors' en la respuesta")
        if "data" not in contenido:
            mensajes_advertencias.append("Falta 'data' en la respuesta")
        if len(mensajes_advertencias) > 0:
            mensaje_advertencia = ", ".join(mensajes_advertencias)
            bitacora.warning(mensaje_advertencia)
            raise MyNotValidAnswerError(mensaje_advertencia.upper() + "\n" + "\n".join(mensajes))
        if contenido["message"]:
            mensaje_info = f"- message: {contenido['message']}"
            bitacora.info(mensaje_info)
            mensajes.append(mensaje_info)
        # Terminar si success es FALSO
        if contenido["success"] is False:
            mensaje_advertencia = f"Falló el envío del archivo porque 'success' es falso: {','.join(contenido['errors'])}"
            bitacora.warning(mensaje_advertencia)
            raise MyNotValidAnswerError(mensaje_advertencia.upper() + "\n" + "\n".join(mensajes))
        # Actualizar el archivo del exhorto al estado RECIBIDO
        archivo.estado = "RECIBIDO"
        archivo.save()
        # Tomar el data que llega por enviar el archivo
        data = contenido["data"]

    # Informar a la bitácora que terminó el envío los archivos
    mensaje_info = "Termina el envío de los archivos."
    mensajes.append(mensaje_info)
    bitacora.info(mensaje_info)

    # Validar que el ULTIMO data tenga el acuse
    if "acuse" not in data or data["acuse"] is None:
        mensaje_advertencia = "Falló porque la respuesta NO tiene acuse"
        bitacora.warning(mensaje_advertencia)
        raise MyAnyError(mensaje_advertencia.upper() + "\n" + "\n".join(mensajes))
    acuse = data["acuse"]

    # Inicializar listado de errores para acumular fallos si los hubiera
    errores = []

    # Validar que el acuse tenga "exhortoId"
    try:
        acuse_exhorto_id = str(acuse["exhortoId"])
        mensaje_info = f"- acuse exhortoId: {acuse_exhorto_id}"
        mensajes.append(mensaje_info)
        bitacora.info(mensaje_info)
    except KeyError:
        errores.append("Faltó exhortoId en el acuse")

    # Validar que el acuse tenga "respuestaOrigenId"
    try:
        acuse_respuesta_origen_id = str(acuse["respuestaOrigenId"])
        mensaje_info = f"- acuse respuestaOrigenId: {acuse_respuesta_origen_id}"
        mensajes.append(mensaje_info)
        bitacora.info(mensaje_info)
    except KeyError:
        errores.append("Faltó respuestaOrigenId en el acuse")

    # Validar que el acuse tenga "fechaHoraRecepcion"
    try:
        acuse_fecha_hora_recepcion_str = str(acuse["fechaHoraRecepcion"])
        acuse_fecha_hora_recepcion = datetime.strptime(acuse_fecha_hora_recepcion_str, "%Y-%m-%d %H:%M:%S")
        mensaje_info = f"- acuse fechaHoraRecepcion: {acuse_fecha_hora_recepcion_str}"
        mensajes.append(mensaje_info)
        bitacora.info(mensaje_info)
    except (KeyError, ValueError):
        errores.append("Faltó o es incorrecta fechaHoraRecepcion en el acuse")

    # Terminar si hubo errores
    if len(errores) > 0:
        mensaje_advertencia = ", ".join(errores)
        bitacora.warning(mensaje_advertencia)
        raise MyAnyError(mensaje_advertencia.upper() + "\n" + "\n".join(mensajes))

    # Actualizar el estado a CONTESTADO y conservar respuesta_origen_id
    exh_exhorto.estado = "CONTESTADO"
    exh_exhorto.respuesta_origen_id = respuesta_origen_id
    exh_exhorto.save()

    # Elaborar mensaje_termino
    mensaje_termino = f"Termina responder exhorto con ID {exh_exhorto_id} al PJ externo."
    mensajes.append(mensaje_termino)
    bitacora.info(mensaje_termino)

    # Entregar mensajes, nombre_archivo y url_publica
    return "\n".join(mensajes), "", ""
