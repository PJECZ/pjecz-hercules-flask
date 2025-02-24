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
@click.option("--estado-clave", type=str, help="Clave INEGI del estado a cambiar.")
def cambiar_endpoints(url_base, estado_clave=""):
    """
    Cambiar todos los endpoints para hacer pruebas entre equipos en red local,
    por ejemplo, use http://192.168.X.X:8000 para que las comunicaciones NO salgan a internet.
    """
    # Si viene estado_clave, solo cambiar los endpoints de ese estado
    if estado_clave != "":
        exh_externo = ExhExterno.query.filter_by(estado_id=estado_clave).first()
        if exh_externo is None:
            click.echo(click.style(f"No se encontró el estado con clave {estado_clave}.", fg="red"))
            return
        exh_externos = [exh_externo]
    else:
        # Si NO viene estado_clave, cambiar todos los endpoints
        exh_externos = ExhExterno.query.filter_by(estatus="A").order_by(ExhExterno.clave).all()
    # Bucle por los exh_externos
    click.echo("Cambiando todos los endpoints: ", nl=False)
    for exh_externo in exh_externos:
        # Cambiar los endpoints
        exh_externo.endpoint_consultar_materias = f"{url_base}/api/v5/materias"
        exh_externo.endpoint_recibir_exhorto = f"{url_base}/api/v5/exh_exhortos"
        exh_externo.endpoint_recibir_exhorto_archivo = f"{url_base}/api/v5/exh_exhortos_archivos/upload"
        exh_externo.endpoint_consultar_exhorto = f"{url_base}/api/v5/exh_exhortos/"  # Debe terminar en /
        exh_externo.endpoint_recibir_respuesta_exhorto = f"{url_base}/api/v5/exh_exhortos/responder"
        exh_externo.endpoint_recibir_respuesta_exhorto_archivo = f"{url_base}/api/v5/exh_exhortos_archivos/responder_upload"
        exh_externo.endpoint_actualizar_exhorto = f"{url_base}/api/v5/exh_exhortos_actualizaciones"
        exh_externo.endpoint_recibir_promocion = f"{url_base}/api/v5/exh_exhortos_promociones"
        exh_externo.endpoint_recibir_promocion_archivo = f"{url_base}/api/v5/exh_exhortos_promociones_archivos/upload"
        # Actualizar
        exh_externo.save()
        click.echo(click.style(f"[{exh_externo.clave}] ", fg="green"), nl=False)
    # Mensaje final
    click.echo()
    if estado_clave != "":
        click.echo(click.style(f"Se han cambiado los endpoints del estado {estado_clave}.", fg="green"))
    else:
        click.echo(click.style("Se han cambiado los endpoints de TODOS los exh_externos.", fg="yellow"))
    click.echo("Ahora puede hacer pruebas de envío en la red local.")


@click.command()
@click.option("--generar-api-keys", is_flag=True, help="Generar API keys con los nombres de los estados.")
def reiniciar(generar_api_keys):
    """Eliminar todos los exh_externos e insertar todos los estados de México con API keys MD5 de sus nombres."""
    database.session.execute(text("TRUNCATE TABLE exh_externos RESTART IDENTITY CASCADE;"))
    database.session.commit()
    click.echo("Se han ELIMINADO todos los exh_externos.")
    # Bucle por los estados de México
    click.echo("Insertando estados de México: ", nl=False)
    for clave, nombre in ESTADOS_CLAVES_NOMBRES.items():
        exh_externo = ExhExterno()
        exh_externo.estado_id = int(clave)
        exh_externo.clave = f"PJ-{clave}"
        exh_externo.descripcion = nombre
        if generar_api_keys:
            exh_externo.api_key = hashlib.md5(nombre.encode()).hexdigest()  # MD5 hash del nombre son 32 caracteres constantes
        exh_externo.save()
        click.echo(click.style(f"[{clave}] ", fg="green"), nl=False)
    # Mensaje final
    click.echo()
    click.echo("Se han INSERTADO todos los estados de México.")
    if generar_api_keys:
        click.echo(click.style("Tienen sus propias API-keys con el MD5 hecho con su nombre.", fg="green"))
    else:
        click.echo(click.style("No tienen API-keys.", fg="yellow"))
    click.echo(click.style("No tienen endpoints.", fg="yellow"))
    click.echo(f"Ahora debe editar los que vaya a usar o ejecutar cambiar_endpoints.")


cli.add_command(cambiar_endpoints)
cli.add_command(reiniciar)
