"""
Alimentar Modulos
"""

import csv
import sys
from pathlib import Path

import click

from lib.safe_string import safe_string
from hercules.blueprints.modulos.models import Modulo

MODULOS_CSV = "seed/modulos.csv"


def alimentar_modulos():
    """Alimentar Modulos"""
    ruta_csv = Path(MODULOS_CSV)
    if not ruta_csv.exists():
        click.echo(f"AVISO: {ruta_csv.name} no se encontró.")
        sys.exit(1)
    if not ruta_csv.is_file():
        click.echo(f"AVISO: {ruta_csv.name} no es un archivo.")
        sys.exit(1)
    click.echo("Alimentando modulos: ", nl=False)
    contador = 0
    with open(ruta_csv, encoding="utf8") as puntero:
        rows = csv.DictReader(puntero)
        for row in rows:
            modulo_id = int(row["modulo_id"])
            nombre = safe_string(row["nombre"], save_enie=True)
            nombre_corto = safe_string(row["nombre_corto"], do_unidecode=False, save_enie=True, to_uppercase=False)
            icono = row["icono"]
            ruta = row["ruta"]
            en_navegacion = row["en_navegacion"] == "1"
            estatus = row["estatus"]
            if modulo_id != contador + 1:
                click.echo(click.style(f"  AVISO: modulo_id {modulo_id} no es consecutivo", fg="red"))
                sys.exit(1)
            Modulo(
                nombre=nombre,
                nombre_corto=nombre_corto,
                icono=icono,
                ruta=ruta,
                en_navegacion=en_navegacion,
                estatus=estatus,
            ).save()
            contador += 1
            click.echo(click.style(".", fg="green"), nl=False)
    click.echo()
    click.echo(click.style(f"  {contador} modulos alimentados.", fg="green"))
