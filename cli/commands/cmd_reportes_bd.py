"""
Reportes BD

  - respaldos: Reporte de respaldos de la BD a un archivo CSV
"""

from datetime import datetime, timedelta
from pathlib import Path
import click
import csv
import os
import sys
import re

from dotenv import load_dotenv

load_dotenv()  # toma las variables de entorno del archivo .env

DIR_RESPALDO_BD = os.getenv("DIR_RESPALDO_BD")


@click.group()
def cli():
    """Reportes BD"""


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


cli.add_command(generar_csv)
