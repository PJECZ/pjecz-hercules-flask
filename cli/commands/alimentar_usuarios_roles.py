"""
Alimentar Usuarios-Roles
"""

import csv
import sys
from pathlib import Path

import click

from hercules.blueprints.roles.models import Rol
from hercules.blueprints.usuarios.models import Usuario
from hercules.blueprints.usuarios_roles.models import UsuarioRol

USUARIOS_ROLES_CSV = "seed/usuarios_roles.csv"


def alimentar_usuarios_roles():
    """Alimentar Uusarios-Roles"""
    ruta = Path(USUARIOS_ROLES_CSV)
    if not ruta.exists():
        click.echo(f"AVISO: {ruta.name} no se encontró.")
        sys.exit(1)
    if not ruta.is_file():
        click.echo(f"AVISO: {ruta.name} no es un archivo.")
        sys.exit(1)
    usuarios_que_no_existen = []
    click.echo("Alimentando usuarios-roles: ", nl=False)
    contador = 0
    with open(ruta, encoding="utf8") as puntero:
        rows = csv.DictReader(puntero)
        for row in rows:
            usuario_id = int(row["usuario_id"])
            usuario = Usuario.query.get(usuario_id)
            if usuario is None:
                click.echo(click.style("!", fg="red"), nl=False)
                usuarios_que_no_existen.append(str(usuario_id))
                continue
            for rol_nombre in row["roles"].split(","):
                rol_nombre = rol_nombre.strip().upper()
                rol = Rol.query.filter_by(nombre=rol_nombre).first()
                if rol is None:
                    continue
                UsuarioRol(
                    usuario=usuario,
                    rol=rol,
                    descripcion=f"{usuario.email} en {rol.nombre}",
                ).save()
                contador += 1
                click.echo(click.style(".", fg="green"), nl=False)
    click.echo()
    if usuarios_que_no_existen:
        click.echo(click.style(f"  AVISO: {','.join(usuarios_que_no_existen)} usuarios no existen.", fg="red"))
    click.echo(click.style(f"  {contador} usuarios-roles alimentados.", fg="green"))
