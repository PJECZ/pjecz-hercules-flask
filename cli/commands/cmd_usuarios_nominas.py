"""
CLI Usuarios Nóminas
"""

from datetime import datetime
import os
import sys

import click
from dotenv import load_dotenv
import requests

from hercules.app import create_app
from hercules.blueprints.usuarios.models import Usuario
from hercules.blueprints.usuarios_nominas.models import UsuarioNomina
from hercules.extensions import database

# Cargar las variables de entorno
load_dotenv()  # Take environment variables from .env
PERSEO_API_URL = os.getenv("PERSEO_API_URL")
PERSEO_API_KEY = os.getenv("PERSEO_API_KEY")
TIMEOUT = 30

# Crear la aplicacion Flask para poder usar la BD
app = create_app()
app.app_context().push()
database.app = app


@click.group()
def cli():
    """Usuarios Nóminas"""


@click.command()
def actualizar():
    """Sincronizar con la API de Perseo"""
    click.echo("Sincronizando Usuarios Nóminas...")

    # Validar que se haya definido PERSEO_URL.
    if PERSEO_API_URL is None:
        click.echo("ERROR: No se ha definido PERSEO_URL.")
        sys.exit(1)

    # Validar que se haya definido PERSEO_API_KEY.
    if PERSEO_API_KEY is None:
        click.echo("ERROR: No se ha definido PERSEO_API_KEY.")
        sys.exit(1)

    # Bucle por los CURP's de Usuarios
    contador = 0
    contador_nuevos = 0
    contador_cambios = 0
    contador_eliminaciones = 0
    for usuario in Usuario.query.filter(Usuario.curp != "").filter_by(estatus="A").order_by(Usuario.curp).all():
        # Consultar a la API
        try:
            respuesta = requests.get(
                f"{PERSEO_API_URL}/timbrados",
                headers={"X-Api-Key": PERSEO_API_KEY},
                params={"curp": usuario.curp},
                timeout=TIMEOUT,
            )
            respuesta.raise_for_status()
        except requests.exceptions.ConnectionError:
            click.echo("ERROR: No hubo respuesta al solicitar usuario")
            sys.exit(1)
        except requests.exceptions.HTTPError as error:
            click.echo("ERROR: Status Code al solicitar usuario: " + str(error))
            sys.exit(1)
        except requests.exceptions.RequestException:
            click.echo("ERROR: Inesperado al solicitar usuario")
            sys.exit(1)
        contenido = respuesta.json()
        if "success" not in contenido:
            click.echo("ERROR: Fallo al solicitar usuario")
            sys.exit(1)
        if contenido["success"] is False:
            if "message" in contenido:
                click.echo(f"\n  AVISO: Fallo en usuario {usuario.curp}: {contenido['message']}")
            else:
                click.echo(f"\n  AVISO: Fallo en usuario {usuario.curp}")
            continue

        # Si no contiene resultados, saltar
        if len(contenido["data"]) == 0:
            click.echo(f"\n  AVISO: La persona con la CURP: {usuario.curp} no tiene timbrados.")
            continue
        datos = contenido["data"]

        # Bucle para eliminar faltantes
        for timbre in UsuarioNomina.query.filter_by(usuario=usuario).filter_by(estatus="A").all():
            encontrado = False
            for dato in datos:
                if dato["id"] == timbre.timbrado_id:
                    encontrado = True
                    break
            if encontrado is False:
                timbre.delete()
                contador_eliminaciones = contador_eliminaciones + 1
                click.echo("-", nl=False)

        # Bucle para añadir nuevos o actualizar timbres
        for dato in datos:
            # Verificar si timbrado_id es nuevo
            usuario_nomina = UsuarioNomina.query.filter_by(timbrado_id=dato["id"]).filter_by(usuario=usuario).filter_by(estatus="A").first()

            # Añadimos un nuevo timbre a nóminas
            if dato["id"] != "" and usuario_nomina is None:
                UsuarioNomina(
                    usuario=usuario,
                    timbrado_id=dato["id"],
                    fecha=datetime.strptime(dato["nomina_fecha_pago"], "%Y-%m-%d").date(),
                    descripcion=dato["nomina_tipo"],
                    archivo_pdf=dato["archivo_pdf"],
                    archivo_xml=dato["archivo_xml"],
                    url_pdf=dato["url_pdf"],
                    url_xml=dato["url_xml"],
                ).save()
                contador_nuevos = contador_nuevos + 1
                click.echo(".", nl=False)
                continue

            # Buscar actualizaciones
            hay_cambios = False
            fecha = datetime.strptime(dato["nomina_fecha_pago"], "%Y-%m-%d").date()
            if fecha != usuario_nomina.fecha:
                hay_cambios = True
            if usuario_nomina.archivo_pdf != dato["archivo_pdf"]:
                hay_cambios = True
            if usuario_nomina.url_pdf != dato["url_pdf"]:
                hay_cambios = True
            if usuario_nomina.archivo_xml != dato["archivo_xml"]:
                hay_cambios = True
            if usuario_nomina.url_xml != dato["url_xml"]:
                hay_cambios = True

            # Hacer actualización del registro
            if hay_cambios:
                usuario_nomina.fecha = fecha
                usuario_nomina.archivo_pdf = dato["archivo_pdf"]
                usuario_nomina.url_pdf = dato["url_pdf"]
                usuario_nomina.archivo_xml = dato["archivo_xml"]
                usuario_nomina.url_xml = dato["url_xml"]
                usuario_nomina.save()
                contador_cambios = contador_cambios + 1
                click.echo("+", nl=False)

        contador += 1
        if contador % 100 == 0:
            click.echo(f"\n  Van {contador}...")

    # Mensaje de termino
    click.echo("")
    click.echo(f"Hubo {contador_nuevos} timbres nuevos copiados.")
    click.echo(f"Hubo {contador_cambios} timbres actualizados.")
    click.echo(f"Hubo {contador_eliminaciones} timbres eliminados.")


cli.add_command(actualizar)
