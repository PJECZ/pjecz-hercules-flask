"""
CLI Ofi Documentos

- enviar_efirma: Envia un documento al motor de firma electrónica.
- enviar_gemini: Envía el contenido de un documento a Gemini.
- enviar_email: Envía un e-mail utilizando Sendgrid.
- enviar_whatsapp: Envía un mensaje por WhatsApp.
- convertir_pdf: Convierte un documento a formato PDF.
"""

import sys

import click

from hercules.blueprints.ofi_documentos.communications.send_to_efirma import enviar_a_efirma
from hercules.blueprints.ofi_documentos.communications.send_to_gemini import enviar_a_gemini
from hercules.blueprints.ofi_documentos.communications.send_to_sendgrid import enviar_a_sendgrid
from hercules.blueprints.ofi_documentos.communications.send_to_whatsapp import enviar_a_whatsapp
from hercules.blueprints.ofi_documentos.conversions.convert_to_pdf import convertir_a_pdf
from hercules.blueprints.ofi_documentos.conversions.back_to_draft import regresar_a_borrador
from lib.exceptions import MyAnyError


@click.group()
def cli():
    """Ofi Documentos"""


@click.command()
@click.argument("ofi_documento_id", type=str)
def convertir_pdf(ofi_documento_id):
    """Convertir a archivo PDF"""
    click.echo("Inicia la conversión a archivo PDF")
    try:
        mensaje_termino, archivo_pdf, archivo_pdf_url = convertir_a_pdf(ofi_documento_id)
    except MyAnyError as error:
        click.echo(click.style(str(error), fg="red"))
        sys.exit(1)
    click.echo(click.style("Archivo PDF: ", fg="green"), nl=False)
    click.echo(archivo_pdf)
    click.echo(click.style("URL archivo PDF: ", fg="green"), nl=False)
    click.echo(archivo_pdf_url)
    click.echo(click.style(mensaje_termino, fg="green"))


@click.command()
@click.argument("ofi_documento_id", type=str)
def enviar_efirma(ofi_documento_id):
    """Enviar al motor de firma electrónica"""
    click.echo("Inicia el envío al motor de firma electrónica")
    try:
        mensaje_termino, _, _ = enviar_a_efirma(ofi_documento_id)
    except MyAnyError as error:
        click.echo(click.style(str(error), fg="red"))
        sys.exit(1)
    click.echo(click.style(mensaje_termino, fg="green"))


@click.command()
@click.argument("ofi_documento_id", type=str)
def enviar_gemini(ofi_documento_id):
    """Enviar contenido a Gemini"""
    click.echo("Inicia el envío del contenido a Gemini")
    try:
        mensaje_termino, _, _ = enviar_a_gemini(ofi_documento_id)
    except MyAnyError as error:
        click.echo(click.style(str(error), fg="red"))
        sys.exit(1)
    click.echo(click.style(mensaje_termino, fg="green"))


@click.command()
@click.argument("ofi_documento_id", type=str)
def enviar_email(ofi_documento_id):
    """Enviar un e-mail por Sendgrid"""
    click.echo("Inicia el envío del e-mail por Sendgrid")
    try:
        mensaje_termino, _, _ = enviar_a_sendgrid(ofi_documento_id)
    except MyAnyError as error:
        click.echo(click.style(str(error), fg="red"))
        sys.exit(1)
    click.echo(click.style(mensaje_termino, fg="green"))


@click.command()
@click.argument("ofi_documento_id", type=str)
def enviar_whatsapp(ofi_documento_id):
    """Enviar un mensaje por WhatsApp"""
    click.echo("Inicia el envío del mensaje por WhatsApp ")
    try:
        mensaje_termino, _, _ = enviar_a_whatsapp(ofi_documento_id)
    except MyAnyError as error:
        click.echo(click.style(str(error), fg="red"))
        sys.exit(1)
    click.echo(click.style(mensaje_termino, fg="green"))


@click.command()
@click.argument("ofi_documento_id", type=str)
def regresar_borrador(ofi_documento_id):
    """Regresar a borrador"""
    click.echo("Inicia el proceso de regresar a borrador")
    try:
        mensaje_termino, _, _ = regresar_a_borrador(ofi_documento_id)
    except MyAnyError as error:
        click.echo(click.style(str(error), fg="red"))
        sys.exit(1)
    click.echo(click.style(mensaje_termino, fg="green"))


cli.add_command(convertir_pdf)
cli.add_command(enviar_efirma)
cli.add_command(enviar_email)
cli.add_command(enviar_gemini)
cli.add_command(enviar_whatsapp)
cli.add_command(regresar_borrador)
