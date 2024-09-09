"""
CLI Bitacoras
"""

from datetime import datetime, timedelta
import locale
import os
import sys

import click
from dotenv import load_dotenv
import sendgrid
from sendgrid.helpers.mail import Email, To, Content, Mail
import pytz

from hercules.app import create_app
from hercules.blueprints.bitacoras.models import Bitacora
from hercules.blueprints.modulos.models import Modulo
from hercules.extensions import database

# Crear la aplicacion Flask para poder usar la BD
app = create_app()
app.app_context().push()
database.app = app

# Cargar las variables de entorno
load_dotenv()

# Configurar el locale
locale.setlocale(locale.LC_TIME, "es_MX.utf8")

# Zona horaria
TIMEZONE = "America/Mexico_City"


@click.group()
def cli():
    """Bitacoras"""


@cli.command()
@click.argument("destinatario", type=str)
@click.option("--probar", is_flag=True, help="Solo probar sin enviar.")
def enviar_cid_procedimientos_diario(destinatario, probar):
    """Enviar reporte diario de la bitacora de CID PROCEDIMIENTOS"""
    click.echo("Inicia enviar reporte diario de la bitacora de CID PROCEDIMIENTOS")

    # Consultar el modulo CID PROCEDIMIENTOS
    modulo = Modulo.query.filter(Modulo.nombre == "CID PROCEDIMIENTOS").first()
    if not modulo:
        click.echo("El modulo CID PROCEDIMIENTOS no existe")
        sys.exit(1)

    # Definir el tiempo para filtrar a partir de las ultimas 24 horas
    desde_dt = datetime.now() - timedelta(hours=24)

    # Consultar la bitacora filtrando por el modulo y las ultimas 24 horas
    bitacoras = (
        Bitacora.query.filter(Bitacora.creado >= desde_dt)
        .filter(Bitacora.modulo_id == modulo.id)
        .filter(Bitacora.estatus == "A")
        .order_by(Bitacora.creado.desc())
        .all()
    )

    # Si no hay bitacoras, terminar
    if len(bitacoras) == 0:
        click.echo(f"No hay bitacoras para enviar creadas desde {desde_dt.strftime('%Y-%m-%d %H:%M:%S')}")
        sys.exit(0)

    # Definir la fecha de hoy en un formato amable
    hoy_str = datetime.now(tz=pytz.timezone(TIMEZONE)).strftime("%d de %B de %Y")

    # Preparar el asunto
    asunto_str = f"Reporte Diario de SICGD Procedimientos - {hoy_str}"

    # Elaborar el contenido del mensaje de correo electronico
    contenidos = []
    contenidos.append("<h2>Reporte Diario de SICGD Procedimientos</h2>")
    contenidos.append(f"<p>Reporte generado el {hoy_str}</p>")
    contenidos.append("<ul>")
    for bitacora in bitacoras:
        contenidos.append(f"<li>{bitacora.usuario.nombre} - {bitacora.descripcion}</li>")
    contenidos.append("</ul>")
    contenido_html = "\n".join(contenidos)

    # Si probar es verdadero, mostrar el asunto y el contenido y terminar
    if probar:
        click.echo(asunto_str)
        click.echo(contenido_html)
        sys.exit(0)

    # Preparar SendGrid
    api_key = os.environ.get("SENDGRID_API_KEY", "")
    if api_key == "":
        click.echo("Falta configurar la variable de entorno SENDGRID_API_KEY")
        sys.exit(0)
    send_grid = sendgrid.SendGridAPIClient(api_key=api_key)

    # Preparar el remitente
    email_sendgrid = os.environ.get("EMAIL_SENDGRID", "plataforma.web@pjecz.gob.mx")
    remitente_email = Email(email_sendgrid)

    # Preparar el destinatario
    destinatario_email = To(destinatario)

    # Enviar el mensaje de correo electronico
    contenido = Content("text/html", contenido_html)
    mail = Mail(remitente_email, destinatario_email, asunto_str, contenido)
    send_grid.client.mail.send.post(request_body=mail.get())

    # Mensaje de termino
    click.echo("Reporte enviado exitosamente")
