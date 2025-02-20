"""
CLI Exh Externos
"""

import hashlib

import click
from sqlalchemy import text

from hercules.app import create_app
from hercules.blueprints.exh_externos.models import ExhExterno
from hercules.extensions import database

app = create_app()
app.app_context().push()
database.app = app

ESTADOS_CLAVES_NOMBRES = {
    "01": "AGUASCALIENTES",
    "02": "BAJA CALIFORNIA",
    "03": "BAJA CALIFORNIA SUR",
    "04": "CAMPECHE",
    "05": "COAHUILA DE ZARAGOZA",
    "06": "COLIMA",
    "07": "CHIAPAS",
    "08": "CHIHUAHUA",
    "09": "CIUDAD DE MEXICO",
    "10": "DURANGO",
    "11": "GUANAJUATO",
    "12": "GUERRERO",
    "13": "HIDALGO",
    "14": "JALISCO",
    "15": "MEXICO",
    "16": "MICHOACAN DE OCAMPO",
    "17": "MORELOS",
    "18": "NAYARIT",
    "19": "NUEVO LEON",
    "20": "OAXACA",
    "21": "PUEBLA",
    "22": "QUERETARO",
    "23": "QUINTANA ROO",
    "24": "SAN LUIS POTOSI",
    "25": "SINALOA",
    "26": "SONORA",
    "27": "TABASCO",
    "28": "TAMAULIPAS",
    "29": "TLAXCALA",
    "30": "VERACRUZ DE IGNACIO DE LA LLAVE",
    "31": "YUCATAN",
    "32": "ZACATECAS",
}


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
    click.echo("Se han cambiado los endpoints de los externos, ahora puede hacer pruebas de envío en la red local.")


@click.command()
def reiniciar():
    """Eliminar todos los exh_externos e insertar todos los estados de México con API keys MD5 de sus nombres."""
    database.session.execute(text("TRUNCATE TABLE exh_externos RESTART IDENTITY CASCADE;"))
    database.session.commit()
    click.echo("Se han eliminado todos los exh_externos.")

    # Bucle por los estados de México
    click.echo("Insertando estados de México: ", nl=False)
    for clave, nombre in ESTADOS_CLAVES_NOMBRES.items():
        exh_externo = ExhExterno()
        exh_externo.estado_id = int(clave)
        exh_externo.clave = f"PJ-{clave}"
        exh_externo.descripcion = nombre
        exh_externo.api_key = hashlib.md5(nombre.encode()).hexdigest()  # MD5 hash del nombre son 32 caracteres constantes
        exh_externo.save()
        click.echo(click.style(f"[{clave}] ", fg="green"), nl=False)

    # Mensaje final
    click.echo()
    click.echo(f"Se han reiniciado los externos, ahora debe ejecutar cambiar_endpoints.")


cli.add_command(cambiar_endpoints)
cli.add_command(reiniciar)
