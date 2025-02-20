"""
CLI Exh Externos
"""

import click

from hercules.app import create_app
from hercules.blueprints.exh_externos.models import ExhExterno
from hercules.extensions import database

app = create_app()
app.app_context().push()
database.app = app


@click.group()
def cli():
    """Exh Externos"""


@click.command()
@click.argument("url_base", type=str)
def cambiar_endpoints(url_base):
    """
    Cambiar todos los endpoints para hacer pruebas entre equipos en red local,
    por ejemplo, use http://192.168.X.X:8000 para que las comunicaciones NO salgan a internet.
    """
    # Bucle por los exh_externos
    click.echo("Cambiando todos los endpoints: ", nl=False)
    for exh_externo in ExhExterno.query.filter_by(estatus="A").order_by(ExhExterno.clave).all():
        # Cambiar los endpoints
        exh_externo.endpoint_consultar_materias = f"{url_base}/api/v5/materias"
        exh_externo.endpoint_recibir_exhorto = f"{url_base}/api/v5/exh_exhortos"
        exh_externo.endpoint_recibir_exhorto_archivo = f"{url_base}/api/v5/exh_exhortos_archivos/upload"
        exh_externo.endpoint_consultar_exhorto = f"{url_base}/api/v5/exh_exhortos/"  # Debe terminar en /
        exh_externo.endpoint_recibir_respuesta_exhorto = f"{url_base}/api/v5/exh_exhortos/responder"
        exh_externo.endpoint_recibir_respuesta_exhorto_archivo = f"{url_base}/api/v5/exh_exhortos_archivos/responder_upload"
        exh_externo.endpoint_actualizar_exhorto = f"{url_base}/api/v5/exh_exhortos_actualizaciones"
        exh_externo.endpoint_recibir_promocion = f"{url_base}/api/v5/exh_exhortos_promociones"
        exh_externo.endpoint_recibir_promocion_archivo = f"{url_base}/api/v5/exh_exhortos_archivos/upload"
        # Actualizar
        exh_externo.save()
        click.echo(click.style(f"[{exh_externo.clave}] ", fg="green"), nl=False)
    # Mensaje final
    click.echo()
    click.echo(f"Se han cambiado con URL base a {url_base} ahora puede hacer pruebas de envío en la red local.")


cli.add_command(cambiar_endpoints)
