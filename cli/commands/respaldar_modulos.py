"""
Respaldar Modulos
"""

import csv
import sys
from pathlib import Path

import click

from hercules.blueprints.modulos.models import Modulo

MODULOS_CSV = "seed/modulos.csv"


def respaldar_modulos():
    """Respaldar Modulos"""
    ruta = Path(MODULOS_CSV)
    if ruta.exists():
        click.echo(f"AVISO: {MODULOS_CSV} ya existe, no voy a sobreescribirlo.")
        sys.exit(1)
    click.echo("Respaldando modulos: ", nl=False)
    contador = 0
    with open(ruta, "w", encoding="utf8") as puntero:
        respaldo = csv.writer(puntero)
        respaldo.writerow(
            [
                "modulo_id",
                "nombre",
                "nombre_corto",
                "icono",
                "ruta",
                "en_navegacion",
                "en_plataforma_carina",
                "en_plataforma_hercules",
                "en_plataforma_web",
                "en_portal_notarias",
                "estatus",
            ]
        )
        for modulo in Modulo.query.order_by(Modulo.id).all():
            respaldo.writerow(
                [
                    modulo.id,
                    modulo.nombre,
                    modulo.nombre_corto,
                    modulo.icono,
                    modulo.ruta,
                    int(modulo.en_navegacion),
                    int(modulo.en_plataforma_carina),
                    int(modulo.en_plataforma_hercules),
                    int(modulo.en_plataforma_web),
                    int(modulo.en_portal_notarias),
                    modulo.estatus,
                ]
            )
            contador += 1
            click.echo(click.style(".", fg="green"), nl=False)
    click.echo()
    click.echo(click.style(f"  {contador} modulos respaldados.", fg="green"))
