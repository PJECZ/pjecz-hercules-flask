"""
Respaldar Inventarios Modelos
"""

import csv
import sys
from pathlib import Path

import click

from hercules.blueprints.inv_modelos.models import InvModelo

INV_MODELOS_CSV = "seed/inv_modelos.csv"


def respaldar_inv_modelos():
    """Respaldar Inventarios Modelos"""
    ruta = Path(INV_MODELOS_CSV)
    if ruta.exists():
        click.echo(f"AVISO: {INV_MODELOS_CSV} ya existe, no voy a sobreescribirlo.")
        sys.exit(1)
    click.echo("Respaldando modelos: ", nl=False)
    contador = 0
    with open(ruta, "w", encoding="utf8") as puntero:
        respaldo = csv.writer(puntero)
        respaldo.writerow(
            [
                "inv_modelo_id",
                "descripcion",
                "inv_marca_id",
                "inv_marca_nombre",
            ]
        )
        for inv_modelo in InvModelo.query.filter_by(estatus="A").order_by(InvModelo.id).all():
            respaldo.writerow(
                [
                    inv_modelo.id,
                    inv_modelo.descripcion,
                    inv_modelo.inv_marca_id,
                    inv_modelo.inv_marca.nombre,
                ]
            )
            contador += 1
            click.echo(click.style(".", fg="green"), nl=False)
    click.echo()
    click.echo(click.style(f"  {contador} modelos respaldados.", fg="green"))
