"""
Alimentar Municipios
"""

import csv
import sys
from pathlib import Path

import click

from hercules.blueprints.municipios.models import Municipio
from lib.safe_string import safe_clave, safe_string

MUNICIPIOS_CSV = "seed/municipios.csv"


def alimentar_municipios():
    """Alimentar Municipios"""
    ruta = Path(MUNICIPIOS_CSV)
    if not ruta.exists():
        click.echo(f"AVISO: {ruta.name} no se encontró.")
        sys.exit(1)
    if not ruta.is_file():
        click.echo(f"AVISO: {ruta.name} no es un archivo.")
        sys.exit(1)
    click.echo("Alimentando municipios: ", nl=False)
    contador = 0
    with open(ruta, encoding="utf8") as puntero:
        rows = csv.DictReader(puntero)
        for row in rows:
            municipio_id = int(row["municipio_id"])
            estado_id = int(row["estado_id"])
            clave = safe_clave(row["clave"])
            nombre = safe_string(row["nombre"], save_enie=True)
            estatus = row["estatus"]
            if municipio_id != contador + 1:
                click.echo(click.style(f"  AVISO: municipio_id {municipio_id} no es consecutivo", fg="red"))
                sys.exit(1)
            Municipio(
                estado_id=estado_id,
                clave=clave,
                nombre=nombre,
                estatus=estatus,
            ).save()
            contador += 1
            click.echo(click.style(".", fg="green"), nl=False)
    click.echo()
    click.echo(click.style(f"  {contador} municipios alimentados.", fg="green"))
