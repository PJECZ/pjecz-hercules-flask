"""
CLI Nominas Personas
"""

import os
import sys

import click
from dotenv import load_dotenv
import requests

from hercules.app import create_app
from hercules.blueprints.nom_personas.models import NomPersona
from hercules.extensions import database

# Crear la aplicacion Flask para poder usar la BD
app = create_app()
app.app_context().push()
database.app = app

# Cargar las variables de entorno
load_dotenv()

# Cargar las variables de entorno de la API de Perseo
PERSEO_API_URL = os.getenv("PERSEO_API_URL")
PERSEO_API_KEY = os.getenv("PERSEO_API_KEY")
TIMEOUT = 24  # segundos


@click.group()
def cli():
    """Nominas Personas"""


@click.command()
def actualizar():
    """Actualizar la tabla de personas haciendo consultas a la API de Perseo"""

    # Validar que PERSEO_API_URL este definida
    if PERSEO_API_URL is None:
        click.echo("FALTA: La variable de entorno PERSEO_API_URL")
        sys.exit(1)

    # Validar que PERSEO_API_KEY este definida
    if PERSEO_API_KEY is None:
        click.echo("FALTA: La variable de entorno PERSEO_API_KEY")
        sys.exit(1)

    # Inicializar el limit y el offset para hacer la paginacion
    limit = None
    offset = 0

    # Bucle para hacer la paginacion
    click.echo(click.style("Inicia la actualizacion: ", fg="green"), nl=False)
    while True:

        # Consultar la API de Perseo
        try:
            respuesta = requests.get(
                f"{PERSEO_API_URL}/v4/personas",
                headers={"X-Api-Key": PERSEO_API_KEY},
                params={"limit": limit, "offset": offset},
                timeout=TIMEOUT,
            )
            respuesta.raise_for_status()
        except requests.exceptions.ConnectionError:
            click.echo("ERROR: No hubo respuesta al solicitar personas")
            sys.exit(1)
        except requests.exceptions.HTTPError as error:
            click.echo("ERROR: Status Code al solicitar personas: " + str(error))
            sys.exit(1)
        except requests.exceptions.RequestException:
            click.echo("ERROR: Inesperado al solicitar personas")
            sys.exit(1)

        # Convertir la respuesta a JSON
        datos = respuesta.json()

        # Validar que success sea parte de datos
        if "success" not in datos:
            click.echo("ERROR: Fallo al solicitar personas porque no tiene success")
            sys.exit(1)

        # Validar que success sea True
        if datos["success"] is False:
            if "message" in datos:
                click.echo(datos["message"])
            else:
                click.echo("FALLO al solicitar personas. No hay mensaje de error.")

        # Validar que haya items en la respuesta
        if len(datos["items"]) == 0:
            click.echo("No hay personas en la respuesta")
            sys.exit(1)

        # Bucle por los resultados de la consulta a la API
        for persona in datos["items"]:
            # Insertar o actualizar la persona en la tabla de personas
            nom_persona = NomPersona.query.filter_by(rfc=persona["rfc"]).first()
            # Si no existe, insertar
            if nom_persona is None:
                nom_persona = NomPersona(
                    rfc=persona["rfc"],
                    nombres=persona["nombres"],
                    apellido_primero=persona["apellido_primero"],
                    apellido_segundo=persona["apellido_segundo"],
                )
                database.session.add(nom_persona)
                click.echo(click.style("+", fg="green"), nl=False)
            else:
                hay_cambio = False
                if nom_persona.nombres != persona["nombres"]:
                    nom_persona.nombres = persona["nombres"]
                    hay_cambio = True
                if nom_persona.apellido_primero != persona["apellido_primero"]:
                    nom_persona.apellido_primero = persona["apellido_primero"]
                    hay_cambio = True
                if nom_persona.apellido_segundo != persona["apellido_segundo"]:
                    nom_persona.apellido_segundo = persona["apellido_segundo"]
                    hay_cambio = True
                if hay_cambio:
                    database.session.add(nom_persona)
                    click.echo(click.style("u", fg="blue"), nl=False)
                else:
                    click.echo(click.style("-", fg="white"), nl=False)

        # Hacer commit de los cambios
        database.session.commit()

        # Definir el limit
        limit = datos["limit"]
        offset += limit

        # Si el offset sobrepasa el total, salir del bucle
        if offset >= datos["total"]:
            break

    # Mensaje final
    click.echo()
    click.echo(click.style("Termina la actualizacion de la tabla de personas", fg="green"))


cli.add_command(actualizar)
