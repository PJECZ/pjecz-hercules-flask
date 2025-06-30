"""
Communications, enviar un mensaje por Sendgrid
"""

from datetime import datetime
import os

from dotenv import load_dotenv
import pytz
import sendgrid
from sendgrid.helpers.mail import Content, Email, Mail, To

from hercules.app import create_app
from hercules.blueprints.ofi_documentos.communications import bitacora
from hercules.blueprints.ofi_documentos.models import OfiDocumento
from hercules.blueprints.ofi_documentos_destinatarios.models import OfiDocumentoDestinatario
from hercules.extensions import database
from lib.exceptions import MyIsDeletedError, MyMissingConfigurationError, MyNotExistsError, MyNotValidParamError
from lib.safe_string import safe_uuid

# Cargar variables de entorno
load_dotenv()
HOST = os.getenv("HOST", "http://localhost:5000")
SENDGRID_API_KEY = os.getenv("SENDGRID_API_KEY", "")
SENDGRID_FROM_EMAIL = os.getenv("SENDGRID_FROM_EMAIL", "")
TZ = os.getenv("TZ", "America/Mexico_City")

# Cargar la aplicación para tener acceso a la base de datos
app = create_app()
app.app_context().push()
database.app = app

TIMEOUT = 60  # segundos


def enviar_a_sendgrid(ofi_documento_id: int) -> tuple[str, str, str]:
    """Enviar un mensaje por Sendgrid"""
    mensajes = []
    mensaje_info = f"Inicia enviar un mensaje por Sendgrid el oficio {ofi_documento_id}"
    mensajes.append(mensaje_info)
    bitacora.info(mensaje_info)

    # TODO: Validar que esté definida la variable de entorno SENDGRID_API_KEY
    if not SENDGRID_API_KEY:
        raise MyMissingConfigurationError("La variable de entorno SENDGRID_API_KEY no está definida")

    # TODO: Validar que esté definida la variable de entorno SENDGRID_FROM_EMAIL
    if not SENDGRID_FROM_EMAIL:
        raise MyMissingConfigurationError("La variable de entorno SENDGRID_FROM_EMAIL no está definida")

    # Consultar el oficio
    ofi_documento_id = safe_uuid(ofi_documento_id)
    if not ofi_documento_id:
        raise MyNotValidParamError("ID de oficio inválido")
    ofi_documento = OfiDocumento.query.get(ofi_documento_id)
    if not ofi_documento:
        raise MyNotExistsError("El oficio no existe")

    # Validar el estatus, que no esté eliminado
    if ofi_documento.estatus != "A":
        raise MyIsDeletedError("El oficio está eliminado")

    # Consultar los destinatarios
    ofi_destinatarios = (
        OfiDocumentoDestinatario.query.filter(OfiDocumentoDestinatario.ofi_documento_id == ofi_documento_id)
        .filter(OfiDocumentoDestinatario.estatus == "A")
        .all()
    )

    # Elaborar el asunto del mensaje
    asunto_str = f"PJECZ Plataforma Web: Oficio {ofi_documento.folio} {ofi_documento.descripcion}"
    mensajes.append(f"- Asunto: {asunto_str}")

    # Elaborar el contenido del mensaje
    fecha_envio = datetime.now(tz=pytz.timezone(TZ)).strftime("%d/%b/%Y %H:%M")
    contenidos = []
    contenidos.append(f"<h2>{asunto_str}</h2>")
    contenidos.append(f"<p>Enviado el {fecha_envio}</p>")
    contenidos.append("<ul>")
    contenidos.append(f"<li>Remitente: <strong>{ofi_documento.usuario.nombre}</strong>, {ofi_documento.usuario.puesto}</li>")
    contenidos.append(f"<li>Folio: <strong>{ofi_documento.folio}</strong></li>")
    contenidos.append(f"<li>Descripción: <strong>{ofi_documento.descripcion}</strong></li>")
    contenidos.append("</ul>")
    contenidos.append("<p>Ingrese a Plataforma Web y de clic a este enlace para ver el oficio:</p>")
    contenidos.append("<ul>")
    contenidos.append(f"<li><a href='{HOST}/ofi_documentos/{ofi_documento.id}'>Oficio {ofi_documento.id}</a></li>")
    contenidos.append("</ul>")
    contenidos.append("<p>Para lograr la meta <em>CERO PAPEL</em> por favor <em>NO IMPRIMA ESTE MENSAJE ni el Oficio.</em></p>")
    contenidos.append("<p>Este mensaje fue enviado por un programa. <em>NO RESPONDA ESTE MENSAJE.</em></p>")
    contenido_html = "\n".join(contenidos)

    # Enviar el e-mail
    send_grid = sendgrid.SendGridAPIClient(api_key=SENDGRID_API_KEY)
    remitente_email = Email(SENDGRID_FROM_EMAIL)
    contenido = Content("text/html", contenido_html)
    mail = Mail(
        from_email=remitente_email,
        subject=asunto_str,
        html_content=contenido,
    )
    for destinatario in ofi_destinatarios:
        if destinatario.con_copia is False:
            mail.add_to(destinatario.usuario.email)
            mensajes.append(f"- Destinatario: {destinatario.usuario.email}")
        else:
            mail.add_cc(destinatario.usuario.email)
            mensajes.append(f"- Con copia: {destinatario.usuario.email}")

    # Enviar mensaje de correo electrónico
    send_grid.client.mail.send.post(request_body=mail.get())

    # Elaborar mensaje_termino
    mensaje_termino = f"Termina enviar un mensaje por Sendgrid."
    mensajes.append(mensaje_termino)
    bitacora.info(mensaje_termino)

    # Entregar mensaje_termino, nombre_archivo y url_publica
    return "\n".join(mensajes), "", ""
