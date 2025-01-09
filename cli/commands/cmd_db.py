"""
CLI Base de Datos
"""

import os
import sys
import csv
import re

from pathlib import Path
from datetime import datetime
import click
from dotenv import load_dotenv

from cli.commands.alimentar_autoridades import alimentar_autoridades
from cli.commands.alimentar_distritos import alimentar_distritos, eliminar_distritos_sin_autoridades
from cli.commands.alimentar_domicilios import alimentar_domicilios
from cli.commands.alimentar_estados import alimentar_estados
from cli.commands.alimentar_materias import alimentar_materias
from cli.commands.alimentar_modulos import alimentar_modulos
from cli.commands.alimentar_municipios import alimentar_municipios
from cli.commands.alimentar_oficinas import alimentar_oficinas
from cli.commands.alimentar_permisos import alimentar_permisos
from cli.commands.alimentar_roles import alimentar_roles
from cli.commands.alimentar_usuarios import alimentar_usuarios
from cli.commands.alimentar_usuarios_roles import alimentar_usuarios_roles
from cli.commands.respaldar_autoridades import respaldar_autoridades
from cli.commands.respaldar_distritos import respaldar_distritos
from cli.commands.respaldar_domicilios import respaldar_domicilios
from cli.commands.respaldar_estados import respaldar_estados
from cli.commands.respaldar_inv_custodias import respaldar_inv_custodias
from cli.commands.respaldar_inv_equipos import respaldar_inv_equipos
from cli.commands.respaldar_inv_marcas import respaldar_inv_marcas
from cli.commands.respaldar_inv_modelos import respaldar_inv_modelos
from cli.commands.respaldar_materias import respaldar_materias
from cli.commands.respaldar_modulos import respaldar_modulos
from cli.commands.respaldar_municipios import respaldar_municipios
from cli.commands.respaldar_oficinas import respaldar_oficinas
from cli.commands.respaldar_roles_permisos import respaldar_roles_permisos
from cli.commands.respaldar_usuarios_roles import respaldar_usuarios_roles
from hercules.app import create_app
from hercules.extensions import database

app = create_app()
app.app_context().push()
database.app = app

load_dotenv()  # Take environment variables from .env

entorno_implementacion = os.environ.get("DEPLOYMENT_ENVIRONMENT", "develop").upper()
DIR_RESPALDO_BD = os.getenv("DIR_RESPALDO_BD")


@click.group()
def cli():
    """Base de Datos"""


@click.command()
def inicializar():
    """Inicializar"""
    if entorno_implementacion == "PRODUCTION":
        click.echo("PROHIBIDO: No se inicializa porque este es el servidor de producción.")
        sys.exit(1)
    database.drop_all()
    database.create_all()
    click.echo("Termina inicializar.")


@click.command()
def alimentar():
    """Alimentar"""
    if entorno_implementacion == "PRODUCTION":
        click.echo("PROHIBIDO: No se alimenta porque este es el servidor de producción.")
        sys.exit(1)
    alimentar_estados()
    alimentar_municipios()
    alimentar_materias()
    alimentar_modulos()
    alimentar_roles()
    alimentar_permisos()
    alimentar_distritos()
    alimentar_autoridades()
    eliminar_distritos_sin_autoridades()
    alimentar_domicilios()
    alimentar_oficinas()
    alimentar_usuarios()
    alimentar_usuarios_roles()
    click.echo("Termina alimentar.")


@click.command()
@click.pass_context
def reiniciar(ctx):
    """Reiniciar ejecuta inicializar y alimentar"""
    ctx.invoke(inicializar)
    ctx.invoke(alimentar)


@click.command()
@click.option("--inventarios", is_flag=True, help="Respaldar inventarios")
def respaldar(inventarios: bool):
    """Respaldar"""
    if inventarios:
        respaldar_inv_marcas()
        respaldar_inv_modelos()
        respaldar_inv_equipos()
        respaldar_inv_custodias()
        click.echo("Termina respaldar inventarios.")
        return
    respaldar_autoridades()
    respaldar_distritos()
    respaldar_domicilios()
    respaldar_estados()
    respaldar_materias()
    respaldar_modulos()
    respaldar_municipios()
    respaldar_oficinas()
    respaldar_roles_permisos()
    respaldar_usuarios_roles()
    click.echo("Termina respaldar.")


@click.command()
def copiar():
    """Copiar registros desde BD Origen a la BD Destino"""
    click.echo("Termina copiar.")


@click.command()
@click.argument("anio_mes", type=str)
@click.option("--output", default="reporte_respaldos_BD.csv", type=str, help="Archivo CSV a escribir")
def generar_csv(anio_mes, output):
    """Reporte de respaldos de BD a un archivo CSV"""
    # Validar el archivo CSV a escribir, que no exista
    ruta = Path(output)
    if ruta.exists():
        click.echo(f"AVISO: {output} existe, no voy a sobreescribirlo.")
        return
    # Validar que el parámetro mes_int sea YYYY-MM
    if not re.match(r"^\d{4}-\d{2}$", anio_mes):
        click.echo(f"ERROR: {anio_mes} no es una fecha valida (YYYY-MM)")
        return
    # Consultar
    click.echo("Elaborando reporte de respaldos BD...")
    # Lectura de archivos dentro del directorio de respaldo
    archivos = []
    nombre_buscado = f"pjecz_plataforma_web-{anio_mes[0:4]}-{anio_mes[5:7]}-"
    for archivo in Path(DIR_RESPALDO_BD).rglob("*"):
        # Consultar archivos que tengan el nombre tal
        if nombre_buscado in archivo.name:
            stat = os.stat(archivo)
            patron_fecha = re.search(r"\d{4}-\d{2}-\d{2}-\d{4}", archivo.name)
            patron_fecha = patron_fecha.group()
            fecha = datetime.strptime(patron_fecha, "%Y-%m-%d-%H%M")
            archivo = {
                "fecha": fecha,
                "nombre": archivo.name,
                "tamanio": stat.st_size / (1024 * 1024),
            }
            archivos.append(archivo)

    # si no hay contenido salir
    if len(archivos) <= 0:
        click.echo("  No se genero archivo de reporte porque no hubo registros.")
        return

    # Escribir el reporte en el archivo CSV
    with open(ruta, "w", encoding="utf8") as puntero:
        reporte = csv.writer(puntero)
        reporte.writerow(
            [
                "Fecha",
                "Nombre del archivo",
                "Tamanio",
            ]
        )
        # Escribir contenido
        for archivo in archivos:
            # Escribir la linea
            reporte.writerow(
                [
                    archivo["fecha"].strftime("%Y-%m-%d %H:%M:%S"),
                    archivo["nombre"],
                    f"{archivo['tamanio']:.2f}",
                ]
            )

    # Mostrar en pantalla resultado
    click.echo(f"  |      Fecha       | Nombre                                      | Tamanio (MB)")
    for archivo in archivos:
        click.echo(f"  + {archivo['fecha'].strftime('%Y-%m-%d %H:%M')} | {archivo['nombre']} | {archivo['tamanio']:.2f}")

    click.echo(f"  {len(archivos)} archivos de respaldo en {ruta.name}")


cli.add_command(inicializar)
cli.add_command(alimentar)
cli.add_command(reiniciar)
cli.add_command(respaldar)
cli.add_command(copiar)
cli.add_command(generar_csv)
