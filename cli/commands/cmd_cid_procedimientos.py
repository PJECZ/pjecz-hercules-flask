"""
CID Procedimientos

- actualizar: Actualizar procedimientos, define cid_area si es CRD
- exportar_xlsx: Exportar Lista Maestra a un archivo xlsx
- crear_pdf: Crear PDF
- respaldar: Respaldar procedimientos autorizados a un archivo CSV
"""

import csv
import sys
from datetime import datetime
from pathlib import Path

import click

from hercules.app import create_app
from hercules.blueprints.autoridades.models import Autoridad
from hercules.blueprints.cid_areas.models import CIDArea
from hercules.blueprints.cid_areas_autoridades.models import CIDAreaAutoridad
from hercules.blueprints.cid_procedimientos.models import CIDProcedimiento
from hercules.blueprints.cid_procedimientos.tasks import exportar_xlsx as task_export_xlsx
from hercules.extensions import database
from lib.exceptions import MyAnyError

# Crear la aplicacion Flask para poder usar la BD
app = create_app()
app.app_context().push()
database.app = app


@click.group()
def cli():
    """CID Procedimientos"""


def buscar_cid_area(autoridad_id: int) -> int:
    """Buscar la primer cid_area que tenga la autoridad_id"""
    cid_area_autoridad = CIDAreaAutoridad.query.filter_by(estatus="A").filter_by(autoridad_id=autoridad_id).first()
    if cid_area_autoridad is None:
        return None
    return cid_area_autoridad.cid_area_id


@click.command()
def actualizar():
    """Actualizar procedimientos, define cid_area si es CRD"""

    # Consultar el area ND - NO DEFINIDO
    cid_area_nd = CIDArea.query.filter_by(clave="CRD").first()
    if cid_area_nd is None:
        click.echo("ERROR: No se encontró el área CRD")
        return

    # Consultar la autoridad ND - NO DEFINIDO
    autoridad_nd = Autoridad.query.filter_by(clave="ND").first()
    if autoridad_nd is None:
        click.echo("ERROR: No se encontró la autoridad ND")
        return

    # Consultar los procedimientos activos que tienen cid_area como NO DEFINIDO
    cid_procedimientos = CIDProcedimiento.query.filter_by(estatus="A").filter_by(cid_area_id=cid_area_nd.id)
    if cid_procedimientos.count() == 0:
        click.echo("No hay procedimientos con área CRD")
        return

    # Bucle por los procedimientos
    contador = 0
    for cid_procedimiento in cid_procedimientos.all():
        cid_area_id = None
        # Opcion 1 Tomar la autoridad_id del procedimiento y buscar la primer area que tenga esa autoridad
        if cid_procedimiento.autoridad_id != autoridad_nd.id:
            cid_area_id = buscar_cid_area(cid_procedimiento.autoridad_id)
            if cid_area_id == cid_area_nd.id:
                cid_area_id = None
        # Opcion 2 Tomar la autoridad_id del usuario y buscar la primer area que tenga esa autoridad
        if cid_area_id is None:
            cid_area_id = buscar_cid_area(cid_procedimiento.usuario.autoridad_id)
            if cid_area_id == cid_area_nd.id:
                cid_area_id = None
        # Opcion 3 No queda otra que dejar el cid_area en CRD
        if cid_area_id is None:
            click.echo(f"Se quedó en CRD el área de {cid_procedimiento.id}: {cid_procedimiento.codigo}")
            continue
        # Si hay cid_area_id, actualizar el procedimiento
        cid_procedimiento.cid_area_id = cid_area_id
        database.session.add(cid_procedimiento)
        contador += 1
        if contador % 10 == 0:
            database.session.commit()
            click.echo(f"  Van {contador}...")

    # Guardar los cambios
    database.session.commit()

    # Mostrar el contador
    click.echo(f"Actualizados {contador} procedimientos")


@click.command()
@click.argument("cid_procedimiento_id", type=int)
def crear_pdf(cid_procedimiento_id):
    """Crear PDF"""
    app.task_queue.enqueue(
        "hercules.blueprints.cid_procedimientos.tasks.crear_pdf",
        cid_procedimiento_id=cid_procedimiento_id,
    )
    click.echo("Crear PDF se está ejecutando en el fondo.")


@click.command()
def exportar_xlsx():
    """Exportar Lista Maestra a un archivo xlsx"""

    # Ejecutar la tarea
    try:
        mensaje_termino, _, _ = task_export_xlsx()
    except MyAnyError as error:
        click.echo(click.style(str(error), fg="red"))
        sys.exit(1)

    # Mensaje de termino
    click.echo(click.style(mensaje_termino, fg="green"))


@click.command()
def respaldar():
    """Respaldar procedimientos autorizados a un archivo CSV"""
    click.echo("Respaldando Procedimientos...")
    salida = Path(f"cid_procedimientos-{datetime.now().strftime('%Y-%m-%d')}.csv")
    contador = 0
    cid_procedimientos = CIDProcedimiento.query.filter_by(estatus="A").filter_by(seguimiento="AUTORIZADO").all()
    with open(salida, "w", encoding="utf8") as puntero:
        respaldo = csv.writer(puntero)
        respaldo.writerow(["id", "titulo", "codigo", "fecha", "autoridad_clave", "seguimiento", "url"])
        for cid_procedimiento in cid_procedimientos:
            respaldo.writerow(
                [
                    cid_procedimiento.id,
                    cid_procedimiento.titulo_procedimiento,
                    cid_procedimiento.codigo,
                    cid_procedimiento.fecha,
                    cid_procedimiento.autoridad.clave,
                    cid_procedimiento.seguimiento,
                    cid_procedimiento.url,
                ]
            )
            contador += 1
            if contador % 100 == 0:
                click.echo(f"  Van {contador}...")
    click.echo(f"Respaldados {contador} procedimientos en {salida}")


cli.add_command(actualizar)
cli.add_command(crear_pdf)
cli.add_command(exportar_xlsx)
cli.add_command(respaldar)
