"""
Communications, enviar al motor de firma electrónica para crear un archivo PDF con firma electrónica avanzada
"""

import requests

from hercules.app import create_app
from hercules.blueprints.ofi_documentos.communications import bitacora
from hercules.extensions import database
from lib.exceptions import MyAnyError, MyConnectionError, MyEmptyError, MyNotExistsError, MyNotValidAnswerError

app = create_app()
app.app_context().push()
database.app = app

TIMEOUT = 60  # segundos


def enviar_a_efirma(ofi_documento_id: int) -> tuple[str, str, str]:
    """Enviar al motor de firma electrónica para crear un archivo PDF con firma electrónica avanzada"""
    mensajes = []
    mensaje_info = "Inicia enviar al motor de firma electrónica."
    mensajes.append(mensaje_info)
    bitacora.info(mensaje_info)

    # Elaborar mensaje_termino
    mensaje_termino = f"Termina enviar al motor de firma electrónica."
    mensajes.append(mensaje_termino)
    bitacora.info(mensaje_termino)

    # Entregar mensaje_termino, nombre_archivo y url_publica
    return "\n".join(mensajes), "", ""
