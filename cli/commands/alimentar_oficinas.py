"""
Alimentar Oficinas
"""

from datetime import datetime
from pathlib import Path
import csv
import sys

import click

from lib.safe_string import safe_clave, safe_string
from hercules.blueprints.distritos.models import Distrito
from hercules.blueprints.domicilios.models import Domicilio
from hercules.blueprints.oficinas.models import Oficina

OFICINAS_CSV = "seed/oficinas.csv"


def alimentar_oficinas():
    """Alimentar Oficinas"""
    ruta = Path(OFICINAS_CSV)
    if not ruta.exists():
        click.echo(f"AVISO: {ruta.name} no se encontró.")
        sys.exit(1)
    if not ruta.is_file():
        click.echo(f"AVISO: {ruta.name} no es un archivo.")
        sys.exit(1)
    click.echo("Alimentando oficinas: ", nl=False)
    contador = 0
    with open(ruta, encoding="utf8") as puntero:
        rows = csv.DictReader(puntero)
        for row in rows:
            oficina_id = int(row["oficina_id"])
            distrito_id = int(row["distrito_id"])
            domicilio_id = int(row["domicilio_id"])
            clave = safe_clave(row["clave"])
            descripcion = safe_string(row["descripcion"], max_len=512, save_enie=True)
            descripcion_corta = safe_string(row["descripcion_corta"], max_len=64, save_enie=True)
            es_jurisdiccional = row["es_jurisdiccional"] == "1"
            puede_agendar_citas = row["puede_agendar_citas"] == "1"
            apertura = datetime.strptime(row["apertura"], "%H:%M:%S")
            cierre = datetime.strptime(row["cierre"], "%H:%M:%S")
            limite_personas = int(row["limite_personas"])
            telefono = safe_string(row["telefono"], max_len=48)
            extension = safe_string(row["extension"], max_len=24)
            estatus = row["estatus"]
            if oficina_id != contador + 1:
                click.echo(click.style(f"  AVISO: oficina_id {oficina_id} no es consecutivo", fg="red"))
                sys.exit(1)
            distrito = Distrito.query.get(distrito_id)
            if distrito is None:
                click.echo(click.style(f"  AVISO: distrito_id {distrito_id} no existe", fg="red"))
                sys.exit(1)
            domicilio = Domicilio.query.get(domicilio_id)
            if domicilio is None:
                click.echo(click.style(f"  AVISO: domicilio_id {domicilio_id} no existe", fg="red"))
                sys.exit(1)
            Oficina(
                domicilio=domicilio,
                distrito=distrito,
                clave=clave,
                descripcion=descripcion,
                descripcion_corta=descripcion_corta,
                es_jurisdiccional=es_jurisdiccional,
                puede_agendar_citas=puede_agendar_citas,
                apertura=apertura,
                cierre=cierre,
                limite_personas=limite_personas,
                telefono=telefono,
                extension=extension,
                estatus=estatus,
            ).save()
            contador += 1
            click.echo(click.style(".", fg="green"), nl=False)
    click.echo()
    click.echo(click.style(f"  {contador} oficinas alimentadas.", fg="green"))
