"""
Ofi Documentos, tareas para ejecutar en el fondo
"""

from hercules.blueprints.ofi_documentos.communications.send_to_efirma import enviar_a_efirma
from hercules.blueprints.ofi_documentos.communications.send_to_gemini import enviar_a_gemini
from hercules.blueprints.ofi_documentos.communications.send_to_sendgrid import enviar_a_sendgrid
from hercules.blueprints.ofi_documentos.communications.send_to_whatsapp import enviar_a_whatsapp
from hercules.blueprints.ofi_documentos.conversions.convert_to_pdf import convertir_a_pdf
from hercules.blueprints.ofi_documentos.conversions.back_to_draft import regresar_a_borrador
from lib.exceptions import MyAnyError
from lib.tasks import set_task_error, set_task_progress


def lanzar_enviar_a_efirma(ofi_documento_id: str) -> str:
    """Lanzar tarea en el fondo para enviar al motor de firma electrónica"""
    set_task_progress(0, "Se ha lanzado la tarea en el fondo enviar al motor de firma electrónica")
    try:
        mensaje_termino, _, _ = enviar_a_efirma(ofi_documento_id)
    except MyAnyError as error:
        mensaje_error = str(error)
        set_task_error(mensaje_error)
        return mensaje_error
    set_task_progress(100, mensaje_termino)
    return mensaje_termino


def lanzar_enviar_a_gemini(ofi_documento_id: str) -> str:
    """Lanzar tarea en el fondo para enviar contenido a Gemini"""
    set_task_progress(0, "Se ha lanzado la tarea en el fondo para enviar contenido a Gemini")
    try:
        mensaje_termino, _, _ = enviar_a_gemini(ofi_documento_id)
    except MyAnyError as error:
        mensaje_error = str(error)
        set_task_error(mensaje_error)
        return mensaje_error
    set_task_progress(100, mensaje_termino)
    return mensaje_termino


def lanzar_enviar_a_sendgrid(ofi_documento_id: str) -> str:
    """Lanzar tarea en el fondo para enviar un mensaje por Sendgrid"""
    set_task_progress(0, "Se ha lanzado la tarea en el fondo para enviar un mensaje por Sendgrid")
    try:
        mensaje_termino, _, _ = enviar_a_sendgrid(ofi_documento_id)
    except MyAnyError as error:
        mensaje_error = str(error)
        set_task_error(mensaje_error)
        return mensaje_error
    set_task_progress(100, mensaje_termino)
    return mensaje_termino


def lanzar_enviar_a_whatsapp(ofi_documento_id: str) -> str:
    """Lanzar tarea en el fondo para enviar un mensaje por WhatsApp"""
    set_task_progress(0, "Se ha lanzado la tarea en el fondo para enviar un mensaje por WhatsApp")
    try:
        mensaje_termino, _, _ = enviar_a_whatsapp(ofi_documento_id)
    except MyAnyError as error:
        mensaje_error = str(error)
        set_task_error(mensaje_error)
        return mensaje_error
    set_task_progress(100, mensaje_termino)
    return mensaje_termino


def lanzar_convertir_a_pdf(ofi_documento_id: str) -> str:
    """Lanzar tarea en el fondo para convertir a PDF"""
    set_task_progress(0, "Se ha lanzado la tarea en el fondo para convertir a PDF")
    try:
        mensaje_termino, _, _ = convertir_a_pdf(ofi_documento_id)
    except MyAnyError as error:
        mensaje_error = str(error)
        set_task_error(mensaje_error)
        return mensaje_error
    set_task_progress(100, mensaje_termino)
    return mensaje_termino


def lanzar_regresar_a_borrador(ofi_documento_id: str) -> str:
    """Lanzar tarea en el fondo para regresar a borrador"""
    set_task_progress(0, "Se ha lanzado la tarea en el fondo para regresar a borrador")
    try:
        mensaje_termino, _, _ = regresar_a_borrador(ofi_documento_id)
    except MyAnyError as error:
        mensaje_error = str(error)
        set_task_error(mensaje_error)
        return mensaje_error
    set_task_progress(100, mensaje_termino)
    return mensaje_termino
