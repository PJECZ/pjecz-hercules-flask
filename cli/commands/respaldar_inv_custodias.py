"""
Respaldar Inventarios Custodias
"""

import csv
import sys
from pathlib import Path

import click

from hercules.blueprints.inv_custodias.models import InvCustodia

INV_CUSTODIAS_CSV = "seed/inv_custodias.csv"


def respaldar_inv_custodias():
    """Respaldar Inventarios Custodias"""
    ruta = Path(INV_CUSTODIAS_CSV)
    if ruta.exists():
        click.echo(f"AVISO: {INV_CUSTODIAS_CSV} ya existe, no voy a sobreescribirlo.")
        sys.exit(1)
    click.echo("Respaldando custodias: ", nl=False)
    contador = 0
    with open(ruta, "w", encoding="utf8") as puntero:
        respaldo = csv.writer(puntero)
        respaldo.writerow(
            [
                "inv_custodia_id",
                "fecha",
                "usuario_id",
                "usuario_nombre",
                "usuario_email",
                "inv_marca_id",
                "inv_marca_nombre",
                "inv_modelo_id",
                "inv_modelo_descripcion",
                "inv_equipo_id",
                "inv_equipo_descripcion",
                "inv_equipo_tipo",
                "inv_equipo_direccion_ip",
                "inv_equipo_direccion_mac",
                "estatus",
            ]
        )
        for inv_custodia in InvCustodia.query.filter_by(estatus="A").order_by(InvCustodia.id).all():
            respaldo.writerow(
                [
                    inv_custodia.id,
                    inv_custodia.fecha,
                    inv_custodia.usuario_id,
                    inv_custodia.usuario.nombre,
                    inv_custodia.usuario.email,
                    inv_custodia.inv_equipo.inv_modelo.inv_marca_id,
                    inv_custodia.inv_equipo.inv_modelo.inv_marca.nombre,
                    inv_custodia.inv_equipo.inv_modelo_id,
                    inv_custodia.inv_equipo.inv_modelo.descripcion,
                    inv_custodia.inv_equipo_id,
                    inv_custodia.inv_equipo.descripcion,
                    inv_custodia.inv_equipo.tipo,
                    inv_custodia.inv_equipo.direccion_ip,
                    inv_custodia.inv_equipo.direccion_mac,
                    inv_custodia.estatus,
                ]
            )
            contador += 1
            click.echo(click.style(".", fg="green"), nl=False)
    click.echo()
    click.echo(click.style(f"  {contador} custodias respaldadas.", fg="green"))
