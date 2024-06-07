"""
Respaldar Oficinas
"""

import csv
import sys
from pathlib import Path

import click

from hercules.blueprints.oficinas.models import Oficina

OFICINAS_CSV = "seed/oficinas.csv"


def respaldar_oficinas():
    """Respaldar Oficinas"""
    ruta = Path(OFICINAS_CSV)
    if ruta.exists():
        click.echo(f"AVISO: {OFICINAS_CSV} ya existe, no voy a sobreescribirlo.")
        sys.exit(1)
    click.echo("Respaldando oficinas: ", nl=False)
    contador = 0
    with open(ruta, "w", encoding="utf8") as puntero:
        respaldo = csv.writer(puntero)
        respaldo.writerow(
            [
                "oficina_id",
                "clave",
                "domicilio_id",
                "distrito_id",
                "descripcion",
                "descripcion_corta",
                "es_jurisdiccional",
                "puede_agendar_citas",
                "apertura",
                "cierre",
                "limite_personas",
                "telefono",
                "extension",
                "estatus",
            ]
        )
        for oficina in Oficina.query.order_by(Oficina.id).all():
            respaldo.writerow(
                [
                    oficina.id,
                    oficina.clave,
                    oficina.domicilio_id,
                    oficina.distrito_id,
                    oficina.descripcion,
                    oficina.descripcion_corta,
                    int(oficina.es_jurisdiccional),
                    int(oficina.puede_agendar_citas),
                    oficina.apertura,
                    oficina.cierre,
                    oficina.limite_personas,
                    oficina.telefono,
                    oficina.extension,
                    oficina.estatus,
                ]
            )
            contador += 1
            click.echo(click.style(".", fg="green"), nl=False)
    click.echo()
    click.echo(click.style(f"  {contador} oficinas respaldadas.", fg="green"))
