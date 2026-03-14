"""
Audiencias

- alimentar: Insertar registros a partir de un archivo CSV
"""

import csv
from datetime import datetime
from pathlib import Path
import sys

import click

from hercules.app import create_app
from hercules.blueprints.audiencias.models import Audiencia
from hercules.blueprints.autoridades.models import Autoridad
from hercules.extensions import database
from lib.safe_string import safe_clave, safe_expediente, safe_string

app = create_app()
app.app_context().push()
database.app = app


@click.group()
def cli():
    """Audiencias"""


@click.command()
@click.argument("archivo_csv", type=click.Path(exists=True))
@click.option("--guardar", is_flag=True, help="Guardar en la BD, por defecto es falso")
def alimentar(archivo_csv, guardar):
    """Insertar registros a partir de un archivo CSV"""

    # Validar que exista el archivo_csv
    archivo_path = Path(archivo_csv)
    if not archivo_path.exists():
        click.echo(f"AVISO: {archivo_path.name} no se encontró.")
        sys.exit(1)
    if not archivo_path.is_file():
        click.echo(f"AVISO: {archivo_path.name} no es un archivo.")
        sys.exit(1)

    # Inicializar el contador
    contador = 0

    # Inicializar la Autoridad
    autoridad = None

    # Leer el archivo
    if guardar:
        click.echo("Alimentando audiencias: ", nl=False)
    else:
        click.echo("Probando audiencias: ", nl=False)
    with open(archivo_path, encoding="utf8") as puntero:
        rows = csv.DictReader(puntero)
        for row in rows:
            try:
                autoridad_clave = safe_clave(row["AUTORIDAD CLAVE"])
                tiempo = datetime.strptime(row["TIEMPO"], "%Y-%m-%d %H:%M:%S")
                tipo_audiencia = safe_string(row["TIPO AUDIENCIA"], max_len=250)
                expediente = safe_expediente(row["EXPEDIENTE"])
                actores = safe_string(row["ACTORES"], max_len=250)
                demandados = safe_string(row["DEMANDADOS"], max_len=250)
            except (IndexError, ValueError):
                click.echo()
                click.echo(f"Error al procesar esta fila: {str(row)}", nl=False)
                sys.exit(1)
            if autoridad is None or autoridad_clave != autoridad.clave:
                autoridad = Autoridad.query.filter_by(clave=autoridad_clave).first()
                if autoridad is None:
                    click.echo(click.style("A", fg="yellow"), nl=False)
                    continue
            if guardar:
                audiencia = Audiencia(
                    autoridad=autoridad,
                    tiempo=tiempo,
                    tipo_audiencia=tipo_audiencia,
                    expediente=expediente,
                    actores=actores,
                    demandados=demandados,
                )
                audiencia.save()
            click.echo(click.style("+", fg="green"), nl=False)
            contador += 1

    # Mensaje final
    click.echo()
    if contador > 0:
        click.echo(click.style(f"{contador} audiencias insertadas.", fg="green"))
    else:
        click.echo(click.style("No se insertó ninguna audiencia.", fg="yellow"))


cli.add_command(alimentar)
