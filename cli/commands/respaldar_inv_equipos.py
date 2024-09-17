"""
Respaldar Inventarios Equipos
"""

import csv
import sys
from pathlib import Path

import click

from hercules.blueprints.inv_equipos.models import InvEquipo

INV_EQUIPOS_CSV = "seed/inv_equipos.csv"


def respaldar_inv_equipos():
    """Respaldar Inventarios Equipos"""
    ruta = Path(INV_EQUIPOS_CSV)
    if ruta.exists():
        click.echo(f"AVISO: {INV_EQUIPOS_CSV} ya existe, no voy a sobreescribirlo.")
        sys.exit(1)
    click.echo("Respaldando equipos: ", nl=False)
    contador = 0
    with open(ruta, "w", encoding="utf8") as puntero:
        respaldo = csv.writer(puntero)
        respaldo.writerow(
            [
                "inv_equipo_id",
                "inv_marca_id",
                "inv_marca_nombre",
                "inv_modelo_id",
                "inv_modelo_descripcion",
                "tipo",
                "fecha_fabricacion_anio",
                "numero_serie",
                "numero_inventario",
                "descripcion",
                "inv_custodia_id",
                "inv_custodia_fecha",
                "usuario_id",
                "usuario_nombre",
                "usuario_email",
            ]
        )
        for inv_equipo in InvEquipo.query.filter_by(estatus="A").order_by(InvEquipo.id).all():
            respaldo.writerow(
                [
                    inv_equipo.id,
                    inv_equipo.inv_modelo.inv_marca_id,
                    inv_equipo.inv_modelo.inv_marca.nombre,
                    inv_equipo.inv_modelo_id,
                    inv_equipo.inv_modelo.descripcion,
                    inv_equipo.tipo,
                    inv_equipo.fecha_fabricacion_anio,
                    inv_equipo.numero_serie,
                    inv_equipo.numero_inventario,
                    inv_equipo.descripcion,
                    inv_equipo.inv_custodia_id,
                    inv_equipo.inv_custodia.fecha,
                    inv_equipo.inv_custodia.usuario_id,
                    inv_equipo.inv_custodia.usuario.nombre,
                    inv_equipo.inv_custodia.usuario.email,
                ]
            )
            contador += 1
            click.echo(click.style(".", fg="green"), nl=False)
    click.echo()
    click.echo(click.style(f"  {contador} equipos respaldados.", fg="green"))
