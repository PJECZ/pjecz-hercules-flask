"""
Communications, Enviar Actualización
"""

import os
from datetime import datetime

import requests
from dotenv import load_dotenv

from hercules.app import create_app
from hercules.blueprints.estados.models import Estado
from hercules.blueprints.exh_exhortos.communications import bitacora
from hercules.blueprints.exh_exhortos.models import ExhExhorto
from hercules.blueprints.exh_exhortos_actualizaciones.models import ExhExhortoActualizacion
from hercules.blueprints.exh_externos.models import ExhExterno
from hercules.blueprints.municipios.models import Municipio
from hercules.extensions import database
from lib.exceptions import MyAnyError, MyConnectionError, MyNotExistsError, MyNotValidAnswerError, MyNotValidParamError
from lib.pwgen import generar_identificador

app = create_app()
app.app_context().push()
database.app = app

load_dotenv()
ESTADO_CLAVE = os.getenv("ESTADO_CLAVE", "")

TIMEOUT = 60  # segundos


def enviar_actualizacion(exh_exhorto_actualizacion_id: int) -> tuple[str, str, str]:
    """Enviar actualización"""
    mensajes = []
    mensaje_info = "Inicia enviar la actualización al PJ externo"
    mensajes.append(mensaje_info)
    bitacora.info(mensaje_info)

    # Consultar la actualización
    exh_exhorto_actualizacion = ExhExhortoActualizacion.query.get(exh_exhorto_actualizacion_id)

    # Validar que exista la actualización
    if exh_exhorto_actualizacion is None:
        mensaje_error = f"No existe la actualización con ID {exh_exhorto_actualizacion_id}"
        bitacora.error(mensaje_error)
        raise MyNotExistsError(mensaje_error)

    # Validar su estado
    if exh_exhorto_actualizacion.estado not in ("POR ENVIAR", "RECHAZADO"):
        mensaje_error = f"La actualización NO se puede enviar porque su estado es {exh_exhorto_actualizacion.estado}"
        bitacora.error(mensaje_error)
        raise MyNotExistsError(mensaje_error)

    # Validar el estado del exhorto
    if exh_exhorto_actualizacion.exh_exhorto.estado in ("ARCHIVADO", "CANCELADO"):
        mensaje_error = "El exhorto está ARCHIVADO o CANCELADO. No se puede enviar la actualización."
        bitacora.error(mensaje_error)
        raise MyNotExistsError(mensaje_error)

    # Validar que este definida la variable de entorno ESTADO_CLAVE
    if ESTADO_CLAVE == "":
        mensaje_error = "No está definida la variable de entorno ESTADO_CLAVE"
        bitacora.error(mensaje_error)
        raise MyNotValidParamError(mensaje_error)

    # Las actualizaciones pueden ser de ORIGEN a DESTINO o de DESTINO a ORIGEN
    sentido = "ORIGEN A DESTINO"  # Por defecto, se asume que es de ORIGEN a DESTINO

    # Tomar el estado de ORIGEN a partir de municipio_origen_id
    municipio = exh_exhorto_actualizacion.exh_exhorto.municipio_origen  # Es una columna foránea
    estado = municipio.estado

    # Si el estado no es el mismo que el de la clave, entonces es de DESTINO a ORIGEN
    if estado.clave == ESTADO_CLAVE:
        sentido = "DESTINO A ORIGEN"

        # Consultar el Estado de DESTINO a partir de municipio_destino_id
        # La columna municipio_destino_id NO es clave foránea, por eso se tiene que hacer las consultas de esta manera
        municipio = Municipio.query.get(exh_exhorto_actualizacion.exh_exhorto.municipio_destino_id)
        if municipio is None:
            mensaje_error = f"No existe el municipio con ID {exh_exhorto_actualizacion.exh_exhorto.municipio_destino_id}"
            bitacora.error(mensaje_error)
            raise MyNotExistsError(mensaje_error)
        estado = Estado.query.get(municipio.estado_id)
        if estado is None:
            mensaje_error = f"No existe el estado con ID {municipio.estado_id}"
            bitacora.error(mensaje_error)
            raise MyNotExistsError(mensaje_error)

    # Informar a la bitácora el sentido
    mensaje_info = f"El sentido es {sentido}."
    mensajes.append(mensaje_info)
    bitacora.info(mensaje_info)

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

    # Si exh_externo no tiene endpoint para enviar actualizaciones
    if exh_externo.endpoint_actualizar_exhorto is None or exh_externo.endpoint_actualizar_exhorto == "":
        mensaje_error = f"No tiene endpoint para enviar actualizaciones el estado {estado.nombre}"
        bitacora.error(mensaje_error)
        raise MyNotExistsError(mensaje_error)

    # Generar un identificador único para la actualización
    actualizacion_origen_id = generar_identificador()

    # Definir los datos de la actualización a enviar
    payload_for_json = {
        "exhortoId": exh_exhorto_actualizacion.exh_exhorto.exhorto_origen_id,
        "actualizacionOrigenId": actualizacion_origen_id,
        "tipoActualizacion": str(exh_exhorto_actualizacion.tipo_actualizacion),
        "fechaHora": exh_exhorto_actualizacion.fecha_hora.strftime("%Y-%m-%d %H:%M:%S"),
        "descripcion": str(exh_exhorto_actualizacion.descripcion),
    }

    # Informar a la bitácora que se va a enviar la actualización
    mensaje_info = "Comienza el envío de la actualización."
    mensajes.append(mensaje_info)
    bitacora.info(mensaje_info)
    for key, value in payload_for_json.items():
        mensaje_info = f"- {key}: {value}"
        mensajes.append(mensaje_info)
        bitacora.info(mensaje_info)

    # Enviar la actualización
    contenido = None
    mensaje_advertencia = ""
    try:
        respuesta = requests.post(
            url=exh_externo.endpoint_actualizar_exhorto,
            headers={"X-Api-Key": exh_externo.api_key},
            timeout=TIMEOUT,
            json=payload_for_json,
        )
        respuesta.raise_for_status()
        contenido = respuesta.json()
    except requests.exceptions.ConnectionError:
        mensaje_advertencia = "No hubo respuesta del servidor al enviar la actualización"
    except requests.exceptions.HTTPError as error:
        mensaje_advertencia = f"Status Code {str(error)} al enviar la actualización"
    except requests.exceptions.RequestException:
        mensaje_advertencia = "Falla desconocida al enviar la actualización"

    # Terminar si hubo mensaje_advertencia
    if mensaje_advertencia != "":
        bitacora.warning(mensaje_advertencia)
        raise MyConnectionError(mensaje_advertencia + "\n" + "\n".join(mensajes))

    # Terminar si NO es correcta estructura de la respuesta
    mensajes_advertencias = []
    if "success" not in contenido or not isinstance(contenido["success"], bool):
        mensajes_advertencias.append("Falta 'success' en la respuesta de la API")
    if "message" not in contenido:
        mensajes_advertencias.append("Falta 'message' en la respuesta de la API")
    if "errors" not in contenido:
        mensajes_advertencias.append("Falta 'errors' en la respuesta de la API")
    if "data" not in contenido:
        mensajes_advertencias.append("Falta 'data' en la respuesta de la API")
    if len(mensajes_advertencias) > 0:
        mensaje_advertencia = ", ".join(mensajes_advertencias)
        bitacora.warning(mensaje_advertencia)
        raise MyNotValidAnswerError(mensaje_advertencia + "\n" + "\n".join(mensajes))
    if contenido["message"]:
        mensaje_info = f"- message: {contenido['message']}"
        bitacora.info(mensaje_info)
        mensajes.append(mensaje_info)

    # Terminar si success es FALSO
    if contenido["success"] is False:
        mensaje_advertencia = f"Falló el envío de la actualización porque 'success' es falso: {','.join(contenido['errors'])}"
        bitacora.warning(mensaje_advertencia)
        raise MyNotValidAnswerError(mensaje_advertencia + "\n" + "\n".join(mensajes))

    # Informar a la bitácora que terminó el envío de la actualización
    mensaje_info = "Termina el envío la actualización."
    mensajes.append(mensaje_info)
    bitacora.info(mensaje_info)

    # Tomar la confirmación de la actualización
    confirmacion = contenido["data"]

    # Inicializar listado de errores para acumular fallos si los hubiera
    errores = []

    # Validar que la confirmación tenga exhortoId
    try:
        confirmacion_exhorto_id = str(confirmacion["exhortoId"])
        mensaje_info = f"- exhortoId: {confirmacion_exhorto_id}"
        mensajes.append(mensaje_info)
        bitacora.info(mensaje_info)
    except KeyError:
        errores.append("Faltó exhortoId en la confirmación")

    # Validar que la confirmación tenga actualizacionOrigenId
    try:
        confirmacion_actulaizacion_origen_id = str(confirmacion["actualizacionOrigenId"])
        mensaje_info = f"- actualizacionOrigenId: {confirmacion_actulaizacion_origen_id}"
        mensajes.append(mensaje_info)
        bitacora.info(mensaje_info)
    except KeyError:
        errores.append("Faltó actualizacionOrigenId en la confirmación")

    # Validar que la confirmación tenga fechaHora
    try:
        confirmacion_fecha_hora_str = str(confirmacion["fechaHora"])
        confirmacion_fecha_hora = datetime.strptime(confirmacion_fecha_hora_str, "%Y-%m-%d %H:%M:%S")
        mensaje_info = f"- fechaHora: {confirmacion_fecha_hora_str}"
        mensajes.append(mensaje_info)
        bitacora.info(mensaje_info)
    except KeyError:
        errores.append("Faltó o es incorrecta fechaHora en la confirmación")

    # Terminar si hubo errores
    if len(errores) > 0:
        mensaje_advertencia = ", ".join(errores)
        bitacora.warning(mensaje_advertencia)
        raise MyAnyError(mensaje_advertencia + "\n" + "\n".join(mensajes))

    # Actualizar el estado a ENVIADO
    exh_exhorto_actualizacion.estado = "ENVIADO"
    exh_exhorto_actualizacion.save()

    # Elaborar mensaje_termino
    mensaje_termino = "Termina enviar la actualización al PJ externo"
    mensajes.append(mensaje_termino)
    bitacora.info(mensaje_termino)

    # Entregar mensaje_termino, nombre_archivo y url_publica
    return "\n".join(mensajes), "", ""
