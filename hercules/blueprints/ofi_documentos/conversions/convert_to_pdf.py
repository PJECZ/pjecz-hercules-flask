"""
Conversions, convertir a PDF
"""

from hercules.app import create_app
from hercules.blueprints.ofi_documentos.conversions import bitacora
from hercules.extensions import database
from lib.exceptions import MyAnyError, MyConnectionError, MyEmptyError, MyNotExistsError, MyNotValidAnswerError

app = create_app()
app.app_context().push()
database.app = app


def convertir_a_pdf(ofi_documento_id: int) -> tuple[str, str, str]:
    """Convertir a PDF"""
    mensajes = []
    mensaje_info = "Inicia convertir a PDF."
    mensajes.append(mensaje_info)
    bitacora.info(mensaje_info)

    # Elaborar mensaje_termino
    mensaje_termino = f"Termina convertir a PDF."
    mensajes.append(mensaje_termino)
    bitacora.info(mensaje_termino)

    # Entregar mensaje_termino, nombre_archivo y url_publica
    return "\n".join(mensajes), "", ""
