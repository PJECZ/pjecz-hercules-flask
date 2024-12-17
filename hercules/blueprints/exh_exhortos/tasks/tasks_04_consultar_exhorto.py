"""
Tareas en el fondo, Exh Exhortos 04 consultar exhorto
"""

import requests

from hercules.blueprints.exh_exhortos.models import ExhExhorto
from hercules.blueprints.exh_exhortos.tasks.tasks_00_bitacora import bitacora
from hercules.blueprints.exh_externos.models import ExhExterno
from hercules.blueprints.municipios.models import Municipio
from lib.exceptions import MyEmptyError, MyNotExistsError

TIMEOUT = 30  # 30 segundos


def task_consultar_exhorto(folio_seguimiento: str = "") -> tuple[str, str, str]:
    """Consultar exhortos"""
    bitacora.info("Inicia consultar exhorto con folio de seguimiento %s", folio_seguimiento)

    # Consultar el exhorto a partir del folio_seguimiento
    exh_exhorto = ExhExhorto.query.filter_by(folio_seguimiento=folio_seguimiento).filter_by(estatus="A").first()

    # Validar que el exhorto exista
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
    mensaje_advertencia = ""
    try:
        respuesta = requests.get(
            url=f"{exh_externo.endpoint_consultar_exhorto}/exh_exhortos/{folio_seguimiento}",
            headers={"X-Api-Key": exh_externo.api_key},
            timeout=TIMEOUT,
        )
    except requests.exceptions.ConnectionError:
        mensaje_advertencia = "No hubo respuesta del servidor al consultar el exhorto"
    except requests.exceptions.HTTPError as error:
        mensaje_advertencia = f"Status Code {str(error)} al consultar el exhorto"
    except requests.exceptions.RequestException:
        mensaje_advertencia = "Falla desconocida al consultar el exhorto"

    # Si fallo la petición
    if mensaje_advertencia != "":
        bitacora.warning(mensaje_advertencia)
        raise MyEmptyError(mensaje_advertencia)

    # Validar el contenido de la respuesta
    contenido = respuesta.json()

    # Validar que se haya tenido éxito

    # Validar el data

    # Validar el contenido de data

    # Guardar los datos de la respuesta en la base de datos

    # Elaborar mensaje_termino
    mensaje_termino = f"Termina consultar exhorto {folio_seguimiento}"
    bitacora.info(mensaje_termino)

    # Entregar mensaje_termino, nombre_archivo y url_publica
    return mensaje_termino, "", ""
