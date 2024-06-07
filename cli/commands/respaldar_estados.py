"""
Respaldar Estados
"""

import csv
import sys
from pathlib import Path

import click

from hercules.blueprints.estados.models import Estado

ESTADOS_CSV = "seed/estados.csv"


def respaldar_estados():
    """Respaldar Estados"""
    ruta = Path(ESTADOS_CSV)
    if ruta.exists():
        click.echo(f"AVISO: {ESTADOS_CSV} ya existe, no voy a sobreescribirlo.")
        sys.exit(1)
    click.echo("Respaldando estados: ", nl=False)
    contador = 0
    with open(ruta, "w", encoding="utf8") as puntero:
        respaldo = csv.writer(puntero)
        respaldo.writerow(
            [
                "estado_id",
                "clave",
                "nombre",
                "estatus",
            ]
        )
        for estado in Estado.query.order_by(Estado.id).all():
            respaldo.writerow(
                [
                    estado.id,
                    estado.clave,
                    estado.nombre,
                    estado.estatus,
                ]
            )
            contador += 1
            click.echo(click.style(".", fg="green"), nl=False)
    click.echo()
    click.echo(click.style(f"  {contador} estados respaldados.", fg="green"))
