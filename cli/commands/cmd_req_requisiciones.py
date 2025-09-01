"""
CLI Req Requisiciones

- convertir_pdf: Convierte un documento a formato PDF.
"""

import sys

import click

from hercules.blueprints.req_requisiciones.conversions.convert_to_pdf import convertir_a_pdf
from lib.exceptions import MyAnyError


@click.group()
def cli():
    """Req Requisiciones"""


@click.command()
@click.argument("req_requisicion_id", type=str)
def convertir_pdf(req_requisicion_id):
    """Convertir a archivo PDF"""
    click.echo("Inicia la conversión a archivo PDF")
    try:
        mensaje_termino, archivo_pdf, archivo_pdf_url = convertir_a_pdf(req_requisicion_id)
    except MyAnyError as error:
        click.echo(click.style(str(error), fg="red"))
        sys.exit(1)
    click.echo(click.style("Archivo PDF: ", fg="green"), nl=False)
    click.echo(archivo_pdf)
    click.echo(click.style("URL archivo PDF: ", fg="green"), nl=False)
    click.echo(archivo_pdf_url)
    click.echo(click.style(mensaje_termino, fg="green"))


cli.add_command(convertir_pdf)
