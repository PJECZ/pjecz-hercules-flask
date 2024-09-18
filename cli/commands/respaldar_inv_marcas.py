"""
Respaldar Inventarios Marcas
"""

import csv
import sys
from pathlib import Path

import click

from hercules.blueprints.inv_marcas.models import InvMarca

INV_MARCAS_CSV = "seed/inv_marcas.csv"


def respaldar_inv_marcas():
    """Respaldar Inventarios Marcas"""
    ruta = Path(INV_MARCAS_CSV)
    if ruta.exists():
        click.echo(f"AVISO: {INV_MARCAS_CSV} ya existe, no voy a sobreescribirlo.")
        sys.exit(1)
    click.echo("Respaldando estados: ", nl=False)
    contador = 0
    with open(ruta, "w", encoding="utf8") as puntero:
        respaldo = csv.writer(puntero)
        respaldo.writerow(
            [
                "marca_id",
                "nombre",
            ]
        )
        for inv_marca in InvMarca.query.filter_by(estatus="A").order_by(InvMarca.id).all():
            respaldo.writerow(
                [
                    inv_marca.id,
                    inv_marca.nombre,
                ]
            )
            contador += 1
            click.echo(click.style(".", fg="green"), nl=False)
    click.echo()
    click.echo(click.style(f"  {contador} marcas respaldadas.", fg="green"))
