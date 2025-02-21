"""
Communications, Consultar Exhorto
"""

import requests

from hercules.app import create_app
from hercules.blueprints.exh_exhortos.communications import bitacora
from hercules.blueprints.exh_exhortos.models import ExhExhorto
from hercules.blueprints.exh_externos.models import ExhExterno
from hercules.blueprints.municipios.models import Municipio
from hercules.extensions import database
from lib.exceptions import MyAnyError, MyConnectionError, MyEmptyError, MyNotExistsError, MyNotValidAnswerError

app = create_app()
app.app_context().push()
database.app = app

TIMEOUT = 60  # segundos


def consultar_exhorto(exh_exhorto_id: int) -> tuple[str, str, str]:
    """Consultar exhortos"""
    bitacora.info("Inicia consultar exhorto al PJ externo.")

    # Consultar el exhorto
    exh_exhorto = ExhExhorto.query.get(exh_exhorto_id)

    # Validar que exista el exhorto
    if exh_exhorto is None:
        mensaje_advertencia = f"No existe el exhorto con ID {exh_exhorto_id}"
        bitacora.error(mensaje_advertencia)
        raise MyNotExistsError(mensaje_advertencia)

    # Validar que su estado sea POR ENVIAR
    if exh_exhorto.estado != "RECIBIDO CON EXITO":
        mensaje_advertencia = f"El exhorto con ID {exh_exhorto_id} no tiene el estado RECIBIDO CON EXITO"
        bitacora.error(mensaje_advertencia)
        raise MyNotExistsError(mensaje_advertencia)

    # Tomar el estado de ORIGEN a partir de municipio_origen, porque es a quien se le va a consultar
    municipio = exh_exhorto.municipio_origen  # Es una columna foránea
    estado = municipio.estado

    # Consultar ExhExterno con el estado
    exh_externo = ExhExterno.query.filter_by(estado_id=estado.id).first()

    # Si ExhExterno no tiene API-key
    if exh_externo.api_key is None or exh_externo.api_key == "":
        mensaje_error = f"No tiene API-key en exh_externos el estado {estado.nombre}"
        bitacora.error(mensaje_error)
        raise MyEmptyError(mensaje_error)

    # Si exh_externo no tiene endpoint para consultar exhortos
    if exh_externo.endpoint_consultar_exhorto is None or exh_externo.endpoint_consultar_exhorto == "":
        mensaje_error = f"No tiene endpoint para consultar exhortos el estado {estado.nombre}"
        bitacora.error(mensaje_error)
        raise MyEmptyError(mensaje_error)

    # Informar a la bitácora que se va a enviar el exhorto
    mensaje = "Pasan las validaciones y comienza la consulta del exhorto."
    bitacora.info(mensaje)

    # Consultar el exhorto
    contenido = None
    mensaje_advertencia = ""
    try:
        respuesta = requests.get(
            url=f"{exh_externo.endpoint_consultar_exhorto}/exh_exhortos/{exh_exhorto.folio_seguimiento}",
            headers={"X-Api-Key": exh_externo.api_key},
            timeout=TIMEOUT,
        )
        respuesta.raise_for_status()
        contenido = respuesta.json()
    except requests.exceptions.ConnectionError:
        mensaje_advertencia = "No hubo respuesta del servidor al consultar el exhorto"
    except requests.exceptions.HTTPError as error:
        mensaje_advertencia = f"Status Code {str(error)} al consultar el exhorto"
    except requests.exceptions.RequestException:
        mensaje_advertencia = "Falla desconocida al consultar el exhorto"

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
        mensaje_advertencia = f"Falló la consulta del exhorto porque 'success' es falso: {','.join(contenido['errors'])}"
        bitacora.warning(mensaje_advertencia)
        raise MyNotValidAnswerError(mensaje_advertencia)

    # Definir los campos que esperamos vengan en el data
    campos = [
        "exhortoOrigenId",
        "folioSeguimiento",
        "estadoDestinoId",
        "estadoDestinoNombre",
        "municipioDestinoId",
        "municipioDestinoNombre",
        "materiaClave",
        "materiaNombre",
        "estadoOrigenId",
        "estadoOrigenNombre",
        "municipioOrigenId",
        "municipioOrigenNombre",
        "juzgadoOrigenId",
        "juzgadoOrigenNombre",
        "numeroExpedienteOrigen",
        "numeroOficioOrigen",
        "tipoJuicioAsuntoDelitos",
        "juezExhortante",
        "partes",
        "fojas",
        "diasResponder",
        "tipoDiligenciacionNombre",
        "fechaOrigen",
        "observaciones",
        "archivos",
        "fechaHoraRecepcion",
        "municipioTurnadoId",
        "municipioTurnadoNombre",
        "areaTurnadoId",
        "areaTurnadoNombre",
        "numeroExhorto",
        "urlInfo",
    ]

    # Validar que vengan los campos en el data
    data = contenido["data"]
    mensajes_campos_valores = []
    mensajes_advertencias = []
    for campo in campos:
        if campo not in data:
            mensajes_advertencias.append(f"Falta {campo}")
            continue
        mensajes_campos_valores.append(f"{campo}: {data['campo']}")

    # Terminar si hubo mensaje_advertencia
    if len(mensajes_advertencias) > 0:
        mensaje_advertencia = f"Fallo la validación de los campos: {', '.join(mensajes_advertencias)}"
        bitacora.warning(mensaje_advertencia)
        raise MyAnyError(mensaje_advertencia)

    # Juntar todos los items del listado en un texto para que sea el mensaje_termino
    mensaje_termino = f"Se consultó el exhorto con ID {exh_exhorto_id} al PJ externo: {', '.join(mensajes_campos_valores)}"
    bitacora.info(mensaje_termino)

    # Entregar mensaje_termino, nombre_archivo y url_publica
    return mensaje_termino, "", ""
