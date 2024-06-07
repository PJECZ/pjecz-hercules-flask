"""
Alimentar Domicilios
"""

from pathlib import Path
import csv
import sys

import click

from lib.safe_string import safe_clave, safe_string
from hercules.blueprints.distritos.models import Distrito
from hercules.blueprints.domicilios.models import Domicilio

DOMICILIOS_CSV = "seed/domicilios.csv"


def alimentar_domicilios():
    """Alimentar Domicilios"""
    ruta = Path(DOMICILIOS_CSV)
    if not ruta.exists():
        click.echo(f"AVISO: {ruta.name} no se encontró.")
        sys.exit(1)
    if not ruta.is_file():
        click.echo(f"AVISO: {ruta.name} no es un archivo.")
        sys.exit(1)
    click.echo("Alimentando domicilios: ", nl=False)
    contador = 0
    with open(ruta, encoding="utf8") as puntero:
        rows = csv.DictReader(puntero)
        for row in rows:
            domicilio_id = int(row["domicilio_id"])
            distrito_clave = safe_clave(row["distrito_clave"])
            edificio = safe_string(row["edificio"], save_enie=True)
            estado = safe_string(row["estado"], save_enie=True)
            municipio = safe_string(row["municipio"], save_enie=True)
            calle = safe_string(row["calle"], save_enie=True)
            num_ext = safe_string(row["num_ext"], save_enie=True)
            num_int = safe_string(row["num_int"], save_enie=True)
            colonia = safe_string(row["colonia"], save_enie=True)
            cp = int(row["cp"])
            estatus = row["estatus"]
            if domicilio_id != contador + 1:
                click.echo(click.style(f"  AVISO: domicilio_id {domicilio_id} no es consecutivo", fg="red"))
                sys.exit(1)
            distrito = Distrito.query.filter_by(clave=distrito_clave).first()
            if distrito is None:
                click.echo(click.style(f"  AVISO: distrito_clave {distrito_clave} no existe", fg="red"))
                sys.exit(1)
            domicilio = Domicilio(
                distrito=distrito,
                edificio=edificio,
                estado=estado,
                municipio=municipio,
                calle=calle,
                num_ext=num_ext,
                num_int=num_int,
                colonia=colonia,
                cp=cp,
                estatus=estatus,
            )
            domicilio.completo = domicilio.elaborar_completo()
            domicilio.save()
            contador += 1
            click.echo(click.style(".", fg="green"), nl=False)
    click.echo()
    click.echo(click.style(f"  {contador} distritos alimentados.", fg="green"))
