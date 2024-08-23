"""
CLI Web Paginas
"""

from datetime import datetime
from pathlib import Path
import os
import re
import sys

import click
from markdown import markdown
from dotenv import load_dotenv

from hercules.app import create_app
from hercules.blueprints.web_paginas.models import WebPagina
from hercules.blueprints.web_ramas.models import WebRama
from hercules.extensions import database

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
@click.argument("rama", type=str)
def actualizar(rama: str, probar: bool = False):
    """Actualizar o agregar las paginas de una rama en la BD"""

    # Si no esta definido ARCHIVISTA_DIR, entonces salir
    if ARCHIVISTA_DIR == "":
        click.echo(click.style("ARCHIVISTA_DIR no esta definido en .env", fg="red"))
        sys.exit(1)

    # Consultar la rama en la BD
    web_rama = WebRama.query.filter_by(nombre=rama).first()

    # Si no existe la rama, entonces salir
    if web_rama is None:
        click.echo(click.echo(click.style(f"La rama {rama} no existe", fg="red")))
        sys.exit(1)

    # Definir el directorio con la rama
    directorio_str = f"{ARCHIVISTA_DIR}/{rama}"

    # Validar que exista y sea un directorio
    if not Path(directorio_str).is_dir():
        click.echo(click.style(f"El directorio {directorio_str} no existe", fg="red"))
        sys.exit(1)

    # Rastrear el directorio de la rama para encontrar los archivos todos los MD
    archivos_md = list(Path(directorio_str).rglob("*.md"))

    # Bucle por cada archivo MD
    contador = 0
    click.echo(f"Actualizando la rama {web_rama.nombre}: ", nl=False)
    for archivo_md in archivos_md:
        contador += 1

        # Inicializar las variables de las columnas de la pagina
        titulo = None
        fecha_modificacion = None

        # Definir la ruta al archivo_md sin el archivo mismo
        ruta = str(archivo_md.parent.relative_to(ARCHIVISTA_DIR))

        # Definir la rama de la pagina
        web_rama_id = web_rama.id

        # Definir la clave de la pagina juntando la clave de la rama y el contador con 4 digitos
        clave = f"{web_rama.clave}-{contador:04d}"

        # Leer el contenido del archivo MD
        with open(archivo_md, "r") as archivo:
            contenido = archivo.read()

            # Extraer el titulo que debe ser la linea con "Title:"
            lineas = contenido.split("\n")
            for linea in lineas:
                if "Title:" in linea:
                    titulo = linea.split(":")[1].strip()
                if "Date:" in linea:
                    date_str = linea.split(":")[1].strip()
                    date_match = re.match(r"(\d{4}-\d{2}-\d{2})", date_str)
                    if date_match is not None:
                        fecha_modificacion = date_match.group(1)
                if titulo is not None and fecha_modificacion is not None:
                    break

            # Si no esta la linea con "Title:", entonces se usa el nombre del archivo sin la extension '.md'
            if titulo is None:
                titulo = archivo_md.name[:-3]

            # Si no hay fecha de modificacion...
            if fecha_modificacion is None:
                # Puede ser que el nombre del archivo tenga YYYY-MM-DD
                fecha_modificacion_match = re.match(r"(\d{4}-\d{2}-\d{2})", archivo_md.name)
                if fecha_modificacion_match is not None:
                    fecha_modificacion = fecha_modificacion_match.group(1)

            # Si no hay fecha de modificacion, se usa la fecha arbitraria 2000-01-01
            if fecha_modificacion is None:
                fecha_modificacion = "2000-01-01"

            # Convertir la fecha de modificacion que es texto a un objeto datetime
            fecha_modificacion = datetime.strptime(fecha_modificacion, "%Y-%m-%d")

        # Si probar es falso, entonces insertar o actualizar la pagina en la BD
        if probar is False:
            # Consultar si la pagina ya existe
            web_pagina = WebPagina.query.filter_by(clave=clave).first()
            # Si no existe, entonces agregarla
            if web_pagina is None:
                web_pagina = WebPagina(
                    clave=clave,
                    titulo=titulo,
                    fecha_modificacion=fecha_modificacion,
                    ruta=ruta,
                    web_rama_id=web_rama_id,
                    contenido=markdown(contenido),
                    estado="BORRADOR",
                )
                database.session.add(web_pagina)
                click.echo(click.style("+", fg="green"), nl=False)
            else:
                # Ya existe, entonces actualizarla si hay cambios
                hubo_cambios = False
                if web_pagina.titulo != titulo:
                    web_pagina.titulo = titulo
                    hubo_cambios = True
                if web_pagina.fecha_modificacion != fecha_modificacion:
                    web_pagina.fecha_modificacion = fecha_modificacion
                    hubo_cambios = True
                if web_pagina.ruta != ruta:
                    web_pagina.ruta = ruta
                    hubo_cambios = True
                if web_pagina.web_rama_id != web_rama_id:
                    web_pagina.web_rama_id = web_rama_id
                    hubo_cambios = True
                if web_pagina.contenido != markdown(contenido):
                    web_pagina.contenido = markdown(contenido)  # Convertir a HTML  antes de guardar
                    hubo_cambios = True
                if web_pagina.estado != "BORRADOR":
                    web_pagina.estado = "BORRADOR"
                    hubo_cambios = True
                if hubo_cambios:
                    click.echo(click.style("u", fg="blue"), nl=False)
            # Guardar los cambios en la BD
            database.session.commit()
        else:
            click.echo(click.style(".", fg="yellow"), nl=False)

    # Mostrar mensaje final
    click.echo()
    click.echo(f"Actualizar ha terminado de leer {contador} archivos md.")


cli.add_command(actualizar)
