"""
Alimentar Estados
"""

import csv
import sys
from pathlib import Path

import click

from hercules.blueprints.estados.models import Estado
from lib.safe_string import safe_clave, safe_string

ESTADOS_CSV = "seed/estados.csv"


def alimentar_estados():
    """Alimentar Estados"""
    ruta = Path(ESTADOS_CSV)
    if not ruta.exists():
        click.echo(f"AVISO: {ruta.name} no se encontró.")
        sys.exit(1)
    if not ruta.is_file():
        click.echo(f"AVISO: {ruta.name} no es un archivo.")
        sys.exit(1)
    click.echo("Alimentando estados: ", nl=False)
    contador = 0
    with open(ruta, encoding="utf8") as puntero:
        rows = csv.DictReader(puntero)
        for row in rows:
            estado_id = int(row["estado_id"])
            clave = safe_clave(row["clave"])
            nombre = safe_string(row["nombre"], save_enie=True)
            estatus = row["estatus"]
            if estado_id != contador + 1:
                click.echo(click.style(f"  AVISO: estado_id {estado_id} no es consecutivo", fg="red"))
                sys.exit(1)
            Estado(
                clave=clave,
                nombre=nombre,
                estatus=estatus,
            ).save()
            contador += 1
            click.echo(click.style(".", fg="green"), nl=False)
    click.echo()
    click.echo(click.style(f"  {contador} estados alimentados.", fg="green"))
