"""
Alimentar Distritos
"""

from pathlib import Path
import csv
import sys

import click

from lib.safe_string import safe_clave, safe_string
from hercules.blueprints.distritos.models import Distrito

DISTRITOS_CSV = "seed/distritos.csv"


def alimentar_distritos():
    """Alimentar Distritos"""
    ruta = Path(DISTRITOS_CSV)
    if not ruta.exists():
        click.echo(f"AVISO: {ruta.name} no se encontró.")
        sys.exit(1)
    if not ruta.is_file():
        click.echo(f"AVISO: {ruta.name} no es un archivo.")
        sys.exit(1)
    click.echo("Alimentando distritos: ", nl=False)
    contador = 0
    with open(ruta, encoding="utf8") as puntero:
        rows = csv.DictReader(puntero)
        for row in rows:
            distrito_id = int(row["distrito_id"])
            clave = safe_clave(row["clave"])
            nombre = safe_string(row["nombre"], save_enie=True)
            nombre_corto = safe_string(row["nombre_corto"], save_enie=True)
            es_distrito_judicial = row["es_distrito_judicial"] == "1"
            es_distrito = row["es_distrito_judicial"] == "1"
            es_jurisdiccional = row["es_distrito_judicial"] == "1"
            estatus = row["estatus"]
            if distrito_id != contador + 1:
                click.echo(click.style(f"  AVISO: distrito_id {distrito_id} no es consecutivo", fg="red"))
                sys.exit(1)
            Distrito(
                clave=clave,
                nombre=nombre,
                nombre_corto=nombre_corto,
                es_distrito_judicial=es_distrito_judicial,
                es_distrito=es_distrito,
                es_jurisdiccional=es_jurisdiccional,
                estatus=estatus,
            ).save()
            contador += 1
            click.echo(click.style(".", fg="green"), nl=False)
    click.echo()
    click.echo(click.style(f"  {contador} distritos alimentados.", fg="green"))


def eliminar_distritos_sin_autoridades():
    """Eliminar Distritos sin Autoridades"""
    click.echo("Eliminando distritos sin autoridades: ", nl=False)
    contador = 0
    for distrito in Distrito.query.filter_by(estatus="A").all():
        autoridades_activas_contador = 0
        for autoridad in distrito.autoridades:
            if autoridad.estatus == "A":
                autoridades_activas_contador += 1
        if autoridades_activas_contador == 0:
            distrito.estatus = "B"
            distrito.save()
            contador += 1
            click.echo(click.style(".", fg="green"), nl=False)
    click.echo()
    click.echo(click.style(f"  {contador} distritos eliminados.", fg="green"))
