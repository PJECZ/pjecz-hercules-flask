"""
Respaldar Municipios
"""

import csv
import sys
from pathlib import Path

import click

from hercules.blueprints.municipios.models import Municipio

MUNICIPIOS_CSV = "seed/municipios.csv"


def respaldar_municipios():
    """Respaldar Municipios"""
    ruta = Path(MUNICIPIOS_CSV)
    if ruta.exists():
        click.echo(f"AVISO: {MUNICIPIOS_CSV} ya existe, no voy a sobreescribirlo.")
        sys.exit(1)
    click.echo("Respaldando municipios: ", nl=False)
    contador = 0
    with open(ruta, "w", encoding="utf8") as puntero:
        respaldo = csv.writer(puntero)
        respaldo.writerow(
            [
                "municipio_id",
                "estado_id",
                "clave",
                "nombre",
                "estatus",
            ]
        )
        for municipio in Municipio.query.order_by(Municipio.id).all():
            respaldo.writerow(
                [
                    municipio.id,
                    municipio.estado_id,
                    municipio.clave,
                    municipio.nombre,
                    municipio.estatus,
                ]
            )
            contador += 1
            click.echo(click.style(".", fg="green"), nl=False)
    click.echo()
    click.echo(click.style(f"  {contador} municipios respaldados.", fg="green"))
