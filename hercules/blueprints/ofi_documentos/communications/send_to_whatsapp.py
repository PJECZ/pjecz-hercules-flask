"""
Communications, enviar a Whatsapp para enviar un mensaje
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


def enviar_a_whatsapp(ofi_documento_id: int) -> tuple[str, str, str]:
    """Enviar a Whatsapp para enviar un mensaje"""
    mensajes = []
    mensaje_info = "Inicia enviar a Whatsapp."
    mensajes.append(mensaje_info)
    bitacora.info(mensaje_info)

    # Elaborar mensaje_termino
    mensaje_termino = f"Termina enviar a Whatsapp."
    mensajes.append(mensaje_termino)
    bitacora.info(mensaje_termino)

    # Entregar mensaje_termino, nombre_archivo y url_publica
    return "\n".join(mensajes), "", ""
