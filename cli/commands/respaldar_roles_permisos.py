"""
Respaldar Roles-Permisos
"""

import csv
import sys
from pathlib import Path

import click

from hercules.blueprints.modulos.models import Modulo
from hercules.blueprints.roles.models import Rol

ROLES_PERMISOS_CSV = "seed/roles_permisos.csv"


def respaldar_roles_permisos():
    """Respaldar Roles-Permisos"""
    ruta = Path(ROLES_PERMISOS_CSV)
    if ruta.exists():
        click.echo(f"AVISO: {ROLES_PERMISOS_CSV} ya existe, no voy a sobreescribirlo.")
        sys.exit(1)
    modulos = Modulo.query.order_by(Modulo.id).all()
    click.echo("Respaldando roles-permisos: ", nl=False)
    contador = 0
    with open(ruta, "w", encoding="utf8") as puntero:
        encabezados = ["rol_id", "nombre"]
        for modulo in modulos:
            encabezados.append(modulo.nombre.lower())
        encabezados.append("estatus")
        respaldo = csv.writer(puntero)
        respaldo.writerow(encabezados)
        for rol in Rol.query.order_by(Rol.id).all():
            renglon = [rol.id, rol.nombre]
            for modulo in modulos:
                permiso_str = ""
                for permiso in rol.permisos:
                    if permiso.modulo_id == modulo.id and permiso.estatus == "A":
                        permiso_str = str(permiso.nivel)
                renglon.append(permiso_str)
            renglon.append(rol.estatus)
            respaldo.writerow(renglon)
            contador += 1
            click.echo(click.style(".", fg="green"), nl=False)
    click.echo()
    click.echo(click.style(f"  {contador} roles-permisos respaldados.", fg="green"))
