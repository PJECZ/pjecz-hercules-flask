"""
CLI Base de Datos
"""

import os
import sys

import click
from dotenv import load_dotenv

from cli.commands.alimentar_autoridades import alimentar_autoridades
from cli.commands.alimentar_distritos import alimentar_distritos, eliminar_distritos_sin_autoridades
from cli.commands.alimentar_domicilios import alimentar_domicilios
from cli.commands.alimentar_estados import alimentar_estados
from cli.commands.alimentar_materias import alimentar_materias
from cli.commands.alimentar_modulos import alimentar_modulos
from cli.commands.alimentar_municipios import alimentar_municipios
from cli.commands.alimentar_oficinas import alimentar_oficinas
from cli.commands.alimentar_permisos import alimentar_permisos
from cli.commands.alimentar_roles import alimentar_roles
from cli.commands.alimentar_usuarios import alimentar_usuarios
from cli.commands.alimentar_usuarios_roles import alimentar_usuarios_roles
from cli.commands.copiar import copiar_tabla
from cli.commands.respaldar_autoridades import respaldar_autoridades
from cli.commands.respaldar_distritos import respaldar_distritos
from cli.commands.respaldar_domicilios import respaldar_domicilios
from cli.commands.respaldar_estados import respaldar_estados
from cli.commands.respaldar_materias import respaldar_materias
from cli.commands.respaldar_modulos import respaldar_modulos
from cli.commands.respaldar_municipios import respaldar_municipios
from cli.commands.respaldar_oficinas import respaldar_oficinas
from cli.commands.respaldar_roles_permisos import respaldar_roles_permisos
from cli.commands.respaldar_usuarios_roles import respaldar_usuarios_roles
from hercules.app import create_app
from hercules.extensions import database

app = create_app()
app.app_context().push()
database.app = app

load_dotenv()  # Take environment variables from .env

entorno_implementacion = os.environ.get("DEPLOYMENT_ENVIRONMENT", "develop").upper()


@click.group()
def cli():
    """Base de Datos"""


@click.command()
def inicializar():
    """Inicializar"""
    if entorno_implementacion == "PRODUCTION":
        click.echo("PROHIBIDO: No se inicializa porque este es el servidor de producción.")
        sys.exit(1)
    database.drop_all()
    database.create_all()
    click.echo("Termina inicializar.")


@click.command()
def alimentar():
    """Alimentar"""
    if entorno_implementacion == "PRODUCTION":
        click.echo("PROHIBIDO: No se alimenta porque este es el servidor de producción.")
        sys.exit(1)
    alimentar_estados()
    alimentar_municipios()
    alimentar_materias()
    alimentar_modulos()
    alimentar_roles()
    alimentar_permisos()
    alimentar_distritos()
    alimentar_autoridades()
    eliminar_distritos_sin_autoridades()
    alimentar_domicilios()
    alimentar_oficinas()
    alimentar_usuarios()
    alimentar_usuarios_roles()
    click.echo("Termina alimentar.")


@click.command()
@click.pass_context
def reiniciar(ctx):
    """Reiniciar ejecuta inicializar y alimentar"""
    ctx.invoke(inicializar)
    ctx.invoke(alimentar)


@click.command()
def respaldar():
    """Respaldar"""
    respaldar_autoridades()
    respaldar_distritos()
    respaldar_domicilios()
    respaldar_estados()
    respaldar_materias()
    respaldar_modulos()
    respaldar_municipios()
    respaldar_oficinas()
    respaldar_roles_permisos()
    respaldar_usuarios_roles()
    click.echo("Termina respaldar.")


@click.command()
def copiar():
    """Copiar registros desde BD Origen a la BD Destino"""
    click.echo("Termina copiar.")


cli.add_command(inicializar)
cli.add_command(alimentar)
cli.add_command(reiniciar)
cli.add_command(respaldar)
cli.add_command(copiar)
