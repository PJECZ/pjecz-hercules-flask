"""
Respaldar Domicilios
"""

import csv
import sys
from pathlib import Path

import click

from hercules.blueprints.domicilios.models import Domicilio

DOMICILIOS_CSV = "seed/domicilios.csv"


def respaldar_domicilios():
    """Respaldar Domicilios"""
    ruta = Path(DOMICILIOS_CSV)
    if ruta.exists():
        click.echo(f"AVISO: {DOMICILIOS_CSV} ya existe, no voy a sobreescribirlo.")
        sys.exit(1)
    click.echo("Respaldando domicilios: ", nl=False)
    contador = 0
    with open(ruta, "w", encoding="utf8") as puntero:
        respaldo = csv.writer(puntero)
        respaldo.writerow(
            [
                "domicilio_id",
                "distrito_clave",
                "edificio",
                "estado",
                "municipio",
                "calle",
                "num_ext",
                "num_int",
                "colonia",
                "cp",
                "estatus",
            ]
        )
        for domicilio in Domicilio.query.order_by(Domicilio.id).all():
            respaldo.writerow(
                [
                    domicilio.id,
                    domicilio.distrito.clave,
                    domicilio.edificio,
                    domicilio.estado,
                    domicilio.municipio,
                    domicilio.calle,
                    domicilio.num_ext,
                    domicilio.num_int,
                    domicilio.colonia,
                    domicilio.cp,
                    domicilio.estatus,
                ]
            )
            contador += 1
            click.echo(click.style(".", fg="green"), nl=False)
    click.echo()
    click.echo(click.style(f"  {contador} domicilios respaldados.", fg="green"))
