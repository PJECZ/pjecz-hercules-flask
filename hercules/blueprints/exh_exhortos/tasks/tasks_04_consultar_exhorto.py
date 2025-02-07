"""
Tareas en el fondo, Exh Exhortos 04 consultar exhorto
"""

import requests

from hercules.blueprints.exh_exhortos.models import ExhExhorto
from hercules.blueprints.exh_exhortos.tasks.tasks_00_bitacora import bitacora
from hercules.blueprints.exh_externos.models import ExhExterno
from hercules.blueprints.municipios.models import Municipio
from lib.exceptions import MyAnyError, MyConnectionError, MyEmptyError, MyNotExistsError

TIMEOUT = 30  # 30 segundos


def task_consultar_exhorto(folio_seguimiento: str = "") -> tuple[str, str, str]:
    """Consultar exhortos"""
    bitacora.info("Inicia consultar exhorto con folio de seguimiento %s", folio_seguimiento)

    # Consultar el exhorto a partir del folio_seguimiento
    exh_exhorto = ExhExhorto.query.filter_by(folio_seguimiento=folio_seguimiento).filter_by(estatus="A").first()

    # Validar que exista el exhorto
    if exh_exhorto is None:
        mensaje_error = f"No existe el exhorto con folio de seguimiento {folio_seguimiento}"
        bitacora.error(mensaje_error)
        raise MyNotExistsError(mensaje_error)

    # Consultar el Estado de destino a partir de municipio_destino_id
    municipio = Municipio.query.get(exh_exhorto.municipio_destino_id)

    # Validar que el municipio exista
    if municipio is None:
        mensaje_error = f"No existe el municipio con ID {exh_exhorto.municipio_destino_id}"
        bitacora.error(mensaje_error)
        raise MyNotExistsError(mensaje_error)

    # Consultar ExhExterno con el estado
    exh_externo = ExhExterno.query.filter_by(estado_id=municipio.estado_id).first()

    # Si ExhExterno no tiene API-key
    if exh_externo.api_key is None or exh_externo.api_key == "":
        mensaje_error = f"No tiene API-key en exh_externos el estado {exh_externo.estado.nombre}"
        bitacora.error(mensaje_error)
        raise MyEmptyError(mensaje_error)

    # Si exh_externo no tiene endpoint para consultar exhortos
    if exh_externo.endpoint_consultar_exhorto is None or exh_externo.endpoint_consultar_exhorto == "":
        mensaje_error = f"No tiene endpoint para consultar exhortos el estado {exh_externo.estado.nombre}"
        bitacora.error(mensaje_error)
        raise MyEmptyError(mensaje_error)

    # Consultar el exhorto
    contenido = None
    mensaje_advertencia = ""
    try:
        respuesta = requests.get(
            url=f"{exh_externo.endpoint_consultar_exhorto}/exh_exhortos/{folio_seguimiento}",
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
    mensaje_advertencia = ""
    for campo in campos:
        if campo not in data:
            mensaje_advertencia = f"Falta {campo} en el data"
            bitacora.warning(mensaje_advertencia)

    # Si hubo mensaje_advertencia
    if mensaje_advertencia != "":
        mensaje_advertencia = "Fallo la validación de los campos de la consulta del exhorto"
        bitacora.warning(mensaje_advertencia)
        raise MyAnyError(mensaje_advertencia)

    # Elaborar un listado con los nombres de los campos y sus valores
    listado = []
    for campo in campos:
        listado.append(f"{campo}: {data[campo]}")

    # Juntar todos los items del listado en un texto para que sea el mensaje_termino
    mensaje_termino = ",".join(listado)
    bitacora.info(mensaje_termino)

    # Entregar mensaje_termino, nombre_archivo y url_publica
    return mensaje_termino, "", ""
