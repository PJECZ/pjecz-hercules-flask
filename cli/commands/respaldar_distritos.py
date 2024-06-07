"""
Respaldar Distritos
"""

import csv
import sys
from pathlib import Path

import click

from hercules.blueprints.distritos.models import Distrito

DISTRITOS_CSV = "seed/distritos.csv"


def respaldar_distritos():
    """Respaldar Distritos"""
    ruta = Path(DISTRITOS_CSV)
    if ruta.exists():
        click.echo(f"AVISO: {DISTRITOS_CSV} ya existe, no voy a sobreescribirlo.")
        sys.exit(1)
    click.echo("Respaldando distritos: ", nl=False)
    contador = 0
    with open(ruta, "w", encoding="utf8") as puntero:
        respaldo = csv.writer(puntero)
        respaldo.writerow(
            [
                "distrito_id",
                "clave",
                "nombre",
                "nombre_corto",
                "es_distrito_judicial",
                "es_distrito",
                "es_jurisdiccional",
                "estatus",
            ]
        )
        for distrito in Distrito.query.order_by(Distrito.id).all():
            respaldo.writerow(
                [
                    distrito.id,
                    distrito.clave,
                    distrito.nombre,
                    distrito.nombre_corto,
                    int(distrito.es_distrito_judicial),
                    int(distrito.es_distrito),
                    int(distrito.es_jurisdiccional),
                    distrito.estatus,
                ]
            )
            contador += 1
            click.echo(click.style(".", fg="green"), nl=False)
    click.echo()
    click.echo(click.style(f"  {contador} distritos respaldados.", fg="green"))
