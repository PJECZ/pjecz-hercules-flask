"""
CLI Google Cloud Secret Manager

- get_secrets: Mostrar los secretos en Google Cloud Secret Manager
"""

import os

import click
from dotenv import load_dotenv
from google.api_core.exceptions import PermissionDenied
from google.cloud import secretmanager

load_dotenv()
GOOGLE_APPLICATION_CREDENTIALS = os.getenv("GOOGLE_APPLICATION_CREDENTIALS")
PROJECT_ID = os.getenv("PROJECT_ID")
SERVICE_PREFIX = os.getenv("SERVICE_PREFIX", "pjecz_hercules_flask")


@click.group()
def cli():
    """Google Cloud Secret Manager"""


@cli.command()
def get_secrets():
    """Mostrar los secretos en Google Cloud Secret Manager"""

    # Validar que la variable de entorno GOOGLE_APPLICATION_CREDENTIALS esté configurada
    if not GOOGLE_APPLICATION_CREDENTIALS:
        click.echo("La variable de entorno GOOGLE_APPLICATION_CREDENTIALS no está configurada.")
        return

    # Validar que la variable de entorno PROJECT_ID esté configurada
    if not PROJECT_ID:
        click.echo("La variable de entorno PROJECT_ID no está configurada.")
        return

    # Crear el cliente para Secret Manager
    client = secretmanager.SecretManagerServiceClient()

    # Definir el directorio parent
    parent = f"projects/{PROJECT_ID}"

    # Bucle por los secretos
    try:
        for secret in client.list_secrets(request={"parent": parent}):
            secret_name = secret.name.split("/")[-1]
            if not secret_name.startswith(SERVICE_PREFIX):
                continue
            secret_version = f"{secret.name}/versions/latest"
            response = client.access_secret_version(request={"name": secret_version})
            payload = response.payload.data.decode("UTF-8")
            click.echo(f"{secret_name}: {payload}")
    except PermissionDenied:
        click.echo("No tienes permisos para acceder a los secretos.")


cli.add_command(get_secrets)
