"""
Communications, Enviar Actualizacion
"""

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
    MyNotValidParamError,
)

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
        mensaje_advertencia = f"No existe la actualización con ID {exh_exhorto_actualizacion_id}"
        bitacora.error(mensaje_advertencia)
        raise MyNotExistsError(mensaje_advertencia)

    # Validar que su estado sea POR ENVIAR
    if exh_exhorto_actualizacion.estado != "PENDIENTE":
        mensaje_advertencia = f"La actualización con ID {exh_exhorto_actualizacion_id} no tiene el estado PENDIENTE"
        bitacora.error(mensaje_advertencia)
        raise MyNotExistsError(mensaje_advertencia)

    # Elaborar mensaje_termino
    mensaje_termino = "Termina enviar la actualización al PJ externo"
    bitacora.info(mensaje_termino)

    # Entregar mensaje_termino, nombre_archivo y url_publica
    return mensaje_termino, "", ""
