"""
CLI cmd_arc_documentos

- Buscar en Expediente Virtual
"""

import os
import sys

import click
from dotenv import load_dotenv

from hercules.app import create_app
from hercules.extensions import database

# Crear la aplicacion Flask para poder usar la BD
app = create_app()
app.app_context().push()
database.app = app

# Cargar las variables de entorno
load_dotenv()

# Carga de Variables de Entorno
EXPEDIENTE_VIRTUAL_API_URL = os.environ.get("EXPEDIENTE_VIRTUAL_API_URL", "")
EXPEDIENTE_VIRTUAL_API_KEY = os.environ.get("EXPEDIENTE_VIRTUAL_API_KEY", "")


@click.group()
def cli():
    """Archivos Documentos"""


@click.command()
@click.argument("num_expediente", type=str)
@click.argument("autoridad_clave", type=str)
def buscar(num_expediente, autoridad_clave):
    """Buscar en expediente virtual"""
    click.echo(num_expediente)
    click.echo(autoridad_clave)
    click.echo(EXPEDIENTE_VIRTUAL_API_URL)
    click.echo(EXPEDIENTE_VIRTUAL_API_KEY)


cli.add_command(buscar)
