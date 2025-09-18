"""
REPSVM

- alimentar: Insertar registros a partir de un archivo CSV
"""

import csv
import os
from pathlib import Path
import sys

import click

from hercules.app import create_app
from hercules.blueprints.distritos.models import Distrito
from hercules.blueprints.repsvm_agresores.models import REPSVMAgresor
from hercules.extensions import database
from lib.safe_string import safe_clave, safe_string, safe_text, safe_url

app = create_app()
app.app_context().push()
database.app = app


@click.group()
def cli():
    """REPSVM"""


@click.command()
@click.argument("archivo_csv", type=click.Path(exists=True))
@click.option("--probar", is_flag=True, help="Probar sin cambiar la BD")
def alimentar(archivo_csv, probar):
    """Insertar registros a partir de un archivo CSV"""

    # Elaborar un diccionario donde la clave del distrito tenga el ID del distrito
    click.echo("Cargando distritos...")
    distritos = {}
    for distrito in Distrito.query.filter_by(es_distrito=True).filter_by(estatus="A").all():
        distritos[distrito.clave] = {"id": distrito.id, "consecutivo": 1}

    # Definir el consecutivo de cada distrito
    for clave, data in distritos.items():
        repsvm_agresor_maximo = (
            REPSVMAgresor.query.filter_by(distrito_id=data["id"])
            .filter_by(estatus="A")
            .order_by(REPSVMAgresor.consecutivo.desc())
            .first()
        )
        if repsvm_agresor_maximo is not None:
            distritos[clave]["consecutivo"] = repsvm_agresor_maximo.consecutivo

    # Mostrar los consecutivos
    click.echo("Consecutivos de cada distrito: ", nl=False)
    for clave, datos in distritos.items():
        click.echo(click.style(f"{clave}->{datos['consecutivo']} ", fg="green"), nl=False)
    click.echo("")

    # Leer el archivo CSV
    registros_nuevos = 0
    registros_omitidos = 0
    registros_fallidos = 0
    click.echo("Alimentando: ", nl=False)
    with open(archivo_csv, newline="", encoding="utf-8") as csvfile:
        lector = csv.DictReader(csvfile)
        for fila in lector:
            # Tomar las columnas del archivo CSV
            distrito_clave = safe_clave(fila["DISTRITO CLAVE"])
            delito_generico = safe_string(fila["DELITO GENERICO"], save_enie=True)
            delito_especifico = safe_string(fila["DELITO ESPECIFICO"], save_enie=True)
            es_publico = fila["ES PUBLICO"].strip().upper() in ("1", "TRUE", "VERDADERO", "SI", "SÍ")
            nombre = safe_string(fila["NOMBRE"], save_enie=True)
            numero_causa = safe_string(fila["NUMERO CAUSA"])
            pena_impuesta = safe_string(fila["PENA IMPUESTA"], save_enie=True)
            observaciones = safe_text(fila["OBSERVACIONES"])
            sentencia_url = safe_url(fila["SENTENCIA URL"])
            tipo_juzgado = safe_string(fila["TIPO JUZGADO"])
            tipo_sentencia = safe_string(fila["TIPO SENTENCIA"])
            # Definir el ID del distrito y su consecutivo
            distrito_id = (distritos[distrito_clave]["id"],)
            consecutivo = (distritos[distrito_clave]["consecutivo"] + 1,)
            # Validar que no exista el registro
            existente = (
                REPSVMAgresor.query.filter_by(nombre=nombre).filter_by(numero_causa=numero_causa).filter_by(estatus="A").first()
            )
            if existente is not None:
                registros_omitidos += 1
                click.echo(f"[{nombre}]", nl=False)
                continue
            # Validar la clave del distrito
            if distrito_clave not in distritos:
                registros_fallidos += 1
                click.echo(f"[DISTRITO CLAVE: {distrito_clave}]", nl=False)
                continue
            # Validar el tipo_juzgado
            if tipo_juzgado not in REPSVMAgresor.TIPOS_JUZGADOS:
                registros_fallidos += 1
                click.echo(f"[TIPO JUZGADO: {tipo_juzgado}]", nl=False)
                continue
            # Validar el tipo_sentencia
            if tipo_sentencia not in REPSVMAgresor.TIPOS_SENTENCIAS:
                registros_fallidos += 1
                click.echo(f"[TIPO SENTENCIA: {tipo_sentencia}]", nl=False)
                continue
            # Crear nuevo registro
            nuevo = REPSVMAgresor(
                distrito_id=distrito_id,
                consecutivo=consecutivo,
                delito_generico=delito_generico,
                delito_especifico=delito_especifico,
                es_publico=es_publico,
                nombre=nombre,
                numero_causa=numero_causa,
                pena_impuesta=pena_impuesta,
                observaciones=observaciones,
                sentencia_url=sentencia_url,
                tipo_juzgado=tipo_juzgado,
                tipo_sentencia=tipo_sentencia,
            )
            if probar is False:
                nuevo.save()
            # Actualizar el consecutivo del distrito
            distritos[distrito_clave]["consecutivo"] = consecutivo
            registros_nuevos += 1
            click.echo(f"[{distritos[distrito_clave]['consecutivo']}]", nl=False)
    click.echo("")

    # Mostrar los consecutivos
    click.echo("Consecutivos de cada distrito: ", nl=False)
    for clave, datos in distritos.items():
        click.echo(click.style(f"{clave}->{datos['consecutivo']} ", fg="green"), nl=False)
    click.echo("")

    # Mensaje final
    if probar:
        click.echo("Prueba completada. No se hicieron cambios en la base de datos.")
    click.echo(f"Registros nuevos: {registros_nuevos}")
    click.echo(f"Registros omitidos (existentes): {registros_omitidos}")


cli.add_command(alimentar)
