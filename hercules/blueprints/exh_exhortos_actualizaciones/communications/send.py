"""
Communications, Enviar Actualizacion
"""

from datetime import datetime

import requests

from hercules.app import create_app
from hercules.blueprints.estados.models import Estado
from hercules.blueprints.exh_exhortos.communications import bitacora
from hercules.blueprints.exh_exhortos.models import ExhExhorto
from hercules.blueprints.exh_externos.models import ExhExterno
from hercules.blueprints.municipios.models import Municipio
from hercules.extensions import database
from lib.exceptions import MyAnyError, MyConnectionError, MyNotExistsError, MyNotValidAnswerError
from lib.pwgen import generar_identificador

app = create_app()
app.app_context().push()
database.app = app

TIMEOUT = 60  # segundos


def enviar_actualizacion(exh_exhorto_actualizacion_id: int) -> tuple[str, str, str]:
    """Enviar actualización"""
    bitacora.info("Inicia enviar la actualización al PJ externo")

    # Consultar la actualización
    exh_exhorto_actualizacion = ExhExhorto.query.get(exh_exhorto_actualizacion_id)

    # Validar que exista la actualización
    if exh_exhorto_actualizacion is None:
        mensaje_error = f"No existe la actualización con ID {exh_exhorto_actualizacion_id}"
        bitacora.error(mensaje_error)
        raise MyNotExistsError(mensaje_error)

    # Validar que su estado sea POR ENVIAR
    if exh_exhorto_actualizacion.estado != "PENDIENTE":
        mensaje_error = f"La actualización con ID {exh_exhorto_actualizacion_id} no tiene el estado PENDIENTE"
        bitacora.error(mensaje_error)
        raise MyNotExistsError(mensaje_error)

    # Consultar el estado de ORIGEN a partir de municipio_origen_id, porque es a quien se le envía la actualización
    municipio = exh_exhorto_actualizacion.exh_exhorto.municipio_origen  # Es una columna foránea
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
    mensaje = "Pasan las validaciones y comienza el envío de la actualización."
    bitacora.info(mensaje)

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
        raise MyConnectionError(mensaje_advertencia)

    # Terminar si NO es correcta estructura de la respuesta
    mensajes_advertencias = []
    if "success" not in contenido or not isinstance(contenido["success"], bool):
        mensajes_advertencias.append("Falta 'success' en la respuesta")
    if "message" not in contenido or not isinstance(contenido["message"], str):
        mensajes_advertencias.append("Falta 'message' en la respuesta")
    if "errors" not in contenido:
        mensajes_advertencias.append("Falta 'errors' en la respuesta")
    if "data" not in contenido:
        mensajes_advertencias.append("Falta 'data' en la respuesta")
    if len(mensajes_advertencias) > 0:
        mensaje_advertencia = ", ".join(mensajes_advertencias)
        bitacora.warning(mensaje_advertencia)
        raise MyNotValidAnswerError(mensaje_advertencia)

    # Terminar si success es FALSO
    if contenido["success"] is False:
        mensaje_advertencia = f"Falló el envío de la actualización porque 'success' es falso: {','.join(contenido['errors'])}"
        bitacora.warning(mensaje_advertencia)
        raise MyNotValidAnswerError(mensaje_advertencia)

    # Informar a la bitácora que terminó el envío de la actualización
    mensaje = "Termina el envío la actualización."
    bitacora.info(mensaje)

    # Tomar la confirmación de la actualización
    confirmacion = contenido["data"]

    # Inicializar listado de errores para acumular fallos si los hubiera
    errores = []

    # Validar que la confirmación tenga exhortoId
    try:
        confirmacion_exhorto_id = str(confirmacion["exhortoId"])
        bitacora.info("Confirmación exhortoId: %s", confirmacion_exhorto_id)
    except KeyError:
        errores.append("Faltó exhortoId en la confirmación")

    # Validar que la confirmación tenga actualizacionOrigenId
    try:
        confirmacion_actulaizacion_origen_id = str(confirmacion["actualizacionOrigenId"])
        bitacora.info("Confirmación actualizacionOrigenId: %s", confirmacion_actulaizacion_origen_id)
    except KeyError:
        errores.append("Faltó actualizacionOrigenId en la confirmación")

    # Validar que la confirmación tenga fechaHora
    try:
        confirmacion_fecha_hora_str = str(confirmacion["fechaHora"])
        confirmacion_fecha_hora = datetime.strptime(confirmacion_fecha_hora_str, "%Y-%m-%d %H:%M:%S")
        bitacora.info("Acuse fechaHora: %s", confirmacion_fecha_hora_str)
    except KeyError:
        errores.append("Faltó o es incorrecta fechaHora en la confirmación")

    # Terminar si hubo errores
    if len(errores) > 0:
        mensaje_advertencia = ", ".join(errores)
        bitacora.warning(mensaje_advertencia)
        raise MyAnyError(mensaje_advertencia)

    # Actualizar el estado a ENVIADO
    exh_exhorto_actualizacion.estado = "ENVIADO"
    exh_exhorto_actualizacion.save()

    # Elaborar mensaje_termino
    mensaje_termino = "Termina enviar la actualización al PJ externo"
    bitacora.info(mensaje_termino)

    # Entregar mensaje_termino, nombre_archivo y url_publica
    return mensaje_termino, "", ""
