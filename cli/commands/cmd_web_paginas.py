"""
CLI Web Paginas
"""

from datetime import date, datetime
from pathlib import Path
import os
import re
import sys

import click
from dotenv import load_dotenv
from markdown import markdown
from unidecode import unidecode

from hercules.app import create_app
from hercules.blueprints.web_paginas.models import WebPagina
from hercules.blueprints.web_ramas.models import WebRama
from hercules.extensions import database
from lib.safe_string import safe_clave, safe_string

# Crear la aplicacion Flask para poder usar la BD
app = create_app()
app.app_context().push()
database.app = app

# Cargar las variables de entorno
load_dotenv()
ARCHIVISTA_DIR = os.getenv("ARCHIVISTA_DIR", "")


@click.group()
def cli():
    """Web Paginas"""


@click.command()
@click.option("--probar", is_flag=True, help="Solo probar sin cambiar la base de datos.")
@click.option("--rama", type=str, help="Clave o nombre de la rama.")
def actualizar(probar: bool = False, rama: str = None):
    """Actualizar o agregar las paginas de una rama en la BD"""

    # Si no esta definido ARCHIVISTA_DIR, entonces salir
    if ARCHIVISTA_DIR == "":
        click.echo(click.style("ARCHIVISTA_DIR no esta definido en .env", fg="red"))
        sys.exit(1)

    # Si no se da la rama, entonces consultar todas las ramas activas
    if rama is None:
        web_ramas = WebRama.query.filter(WebRama.estatus == "A").order_by(WebRama.clave).all()
    else:
        # Consultar el parametro rama como clave en web_ramas
        web_rama = None
        clave = safe_clave(rama)
        if clave is not None:
            web_rama = WebRama.query.filter_by(clave=clave).first()
        # Si no existe como clave, entonces consultar por nombre
        if web_rama is None:
            nombre = safe_string(rama, save_enie=True)
            web_rama = WebRama.query.filter_by(nombre=nombre).first()
        # Si no existe la rama, entonces mostrar error y salir
        if web_rama is None:
            click.echo(click.echo(click.style(f"La rama {rama} no existe", fg="red")))
            sys.exit(1)
        web_ramas = [web_rama]

    # Bucle por cada rama
    contador = 0
    for web_rama in web_ramas:

        # Definir el directorio con la rama
        directorio_str = f"{ARCHIVISTA_DIR}/{web_rama.nombre}"

        # Validar que exista y sea un directorio
        if not Path(directorio_str).is_dir():
            click.echo(click.style(f"El directorio {directorio_str} no existe", fg="red"))
            continue

        # Rastrear el directorio de la rama para encontrar los archivos todos los MD
        archivos_md = list(Path(directorio_str).rglob("*.md"))

        # Bucle por cada archivo MD
        click.echo(f"Actualizando la rama {web_rama.clave}:", nl=False)
        for archivo_md in archivos_md:
            contador += 1

            # Inicializar las variables con sus valores por defecto
            titulo = None
            resumen = ""
            fecha_modificacion = None
            etiquetas = ""
            vista_previa = ""
            estado = "PUBLICAR"

            # Definir la ruta al archivo_md sin el archivo mismo
            ruta = str(archivo_md.parent.relative_to(ARCHIVISTA_DIR))

            # Definir la clave de la pagina juntando la clave de la rama y el contador con 4 digitos
            clave = f"{web_rama.clave}-{contador:04d}"

            # Leer el contenido del archivo MD
            with open(file=archivo_md, mode="r", encoding="UTF8") as archivo:
                # Separar el contenido del archivo en lineas
                lineas = archivo.read().split("\n")

                # Inicializar lineas_nuevas como lista vacia para guardar las lineas que no son metadatos
                lineas_nuevas = []

                # Buscar en las lineas los metadatos
                hay_contenido = False
                for linea in lineas:
                    if linea.startswith("Title:"):
                        titulo = safe_string(linea[6:].strip(), do_unidecode=False, save_enie=True, to_uppercase=False)
                    elif linea.startswith("Summary:"):
                        resumen = safe_string(
                            linea[8:].strip(), do_unidecode=False, save_enie=True, to_uppercase=False, max_len=1000
                        )
                    elif linea.startswith("Date:"):
                        date_match = re.match(r"(\d{4}-\d{2}-\d{2})", linea[5:].strip())
                        if date_match is not None:
                            fecha_modificacion = date_match.group(1)  # Nos quedamos solo con la fecha en formato YYYY-MM-DD
                    elif linea.startswith("Tags:"):
                        etiquetas = safe_string(linea[6:].strip(), save_enie=True, to_uppercase=False, max_len=256)
                    elif linea.startswith("Preview:"):
                        vista_previa = linea[9:].strip()  # Debe ser un archivo de imagen
                    elif linea.startswith("Status:"):
                        linea_estado = safe_string(linea[8:].strip()).upper()  # En Pelican puede ser DRAFT, HIDDEN o PUBLISHED
                        if linea_estado == "DRAFT":
                            estado = "BORRADOR"
                        elif linea_estado == "HIDDEN":
                            estado = "ARCHIVAR"
                    else:
                        linea_limpia = linea.strip()
                        if linea_limpia != "":
                            hay_contenido = True
                        lineas_nuevas.append(linea_limpia)  # Si no es metadato, entonces guardar la linea

                # Si NO hay textos en las lineas se omite este archivo
                if hay_contenido is False or len(lineas_nuevas) == 0:
                    click.echo(click.style("0", fg="red"), nl=False)
                    continue

                # Unir las lineas que no son metadatos
                contenido_html = markdown("\n".join(lineas_nuevas), extensions=["tables"])

                # Si NO hay titulo, entonces se usa el nombre del archivo sin la extension '.md'
                if titulo is None or titulo == "":
                    titulo = archivo_md.name[:-3]

                # Si NO hay fecha de modificacion...
                if fecha_modificacion is None:
                    # Entonces se busca en el nombre del archivo algo como YYYY-MM-DD
                    fecha_modificacion_match = re.match(r"(\d{4}-\d{2}-\d{2})", archivo_md.name)
                    if fecha_modificacion_match is not None:
                        fecha_modificacion = fecha_modificacion_match.group(1)

                # Si NO hay fecha de modificacion, se usa la fecha fija 2000-01-01
                if fecha_modificacion is None:
                    fecha_modificacion = "2000-01-01"

                # Convertir la fecha de modificacion de texto a datetime
                fecha_modificacion = datetime.strptime(fecha_modificacion, "%Y-%m-%d").date()

            # Validar clave
            if not isinstance(clave, str) or clave == "":
                click.echo(click.style("c", fg="red"), nl=False)
                continue

            # Validar titulo
            if not isinstance(titulo, str) or titulo == "":
                click.echo(click.style("t", fg="red"), nl=False)
                continue

            # Validar fecha de modificacion
            if not isinstance(fecha_modificacion, date):
                click.echo(click.style("f", fg="red"), nl=False)
                continue

            # Validar ruta
            if not isinstance(ruta, str) or ruta == "":
                click.echo(click.style("r", fg="red"), nl=False)
                continue

            # Validar contenido_html
            if not isinstance(contenido_html, str) or contenido_html == "":
                click.echo(click.style("h", fg="red"), nl=False)
                continue

            # Si probar es falso, entonces insertar o actualizar la pagina en la BD
            if probar is False:
                # Consultar la pagina por la clave unica
                web_pagina = WebPagina.query.filter_by(clave=clave).first()
                # Si NO existe, entonces agregarla
                if web_pagina is None:
                    web_pagina = WebPagina(
                        web_rama_id=web_rama.id,
                        clave=clave,
                        titulo=titulo,
                        resumen=resumen,
                        fecha_modificacion=fecha_modificacion,
                        ruta=ruta,
                        etiquetas=etiquetas,
                        vista_previa=vista_previa,
                        contenido=contenido_html,
                        estado=estado,
                    )
                    try:
                        web_pagina.save()
                    except ValueError as error:
                        database.session.rollback()
                        click.echo(click.style(f"{str(error)} {repr(web_pagina)}", fg="red"), nl=False)
                    click.echo(click.style("+", fg="green"), nl=False)
                else:
                    # Ya existe, entonces actualizarla solo si hay cambios
                    hubo_cambios = False
                    if web_pagina.titulo != titulo:
                        web_pagina.titulo = titulo
                        hubo_cambios = True
                    if web_pagina.resumen != resumen:
                        web_pagina.resumen = resumen
                        hubo_cambios = True
                    if web_pagina.fecha_modificacion != fecha_modificacion:
                        web_pagina.fecha_modificacion = fecha_modificacion
                        hubo_cambios = True
                    if web_pagina.ruta != ruta:
                        web_pagina.ruta = ruta
                        hubo_cambios = True
                    if web_pagina.etiquetas != etiquetas:
                        web_pagina.etiquetas = etiquetas
                        hubo_cambios = True
                    if web_pagina.vista_previa != vista_previa:
                        web_pagina.vista_previa = vista_previa
                        hubo_cambios = True
                    if web_pagina.contenido != contenido_html:
                        web_pagina.contenido = contenido_html
                        hubo_cambios = True
                    if web_pagina.estado != estado:
                        web_pagina.estado = estado
                        hubo_cambios = True
                    if hubo_cambios:
                        web_pagina.save()
                        click.echo(click.style("u", fg="blue"), nl=False)
            else:
                click.echo(click.style(".", fg="yellow"), nl=False)

        # Termina la rama, poner avance de linea
        click.echo()

    # Mostrar mensaje final
    click.echo(f"Actualizar ha terminado de procesar {contador} archivos md.")


cli.add_command(actualizar)
