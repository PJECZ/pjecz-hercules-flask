"""
CLI Edictos

refrescar - Refrescar la tabla edictos con los archivos en GCStorage
"""

import os
import re
import sys
from datetime import date, datetime
from pathlib import Path
from urllib.parse import unquote, urlparse

import click
from dateutil.tz import tzlocal
from dotenv import load_dotenv
from google.cloud import storage
from google.cloud.exceptions import NotFound
from hashids import Hashids

from hercules.app import create_app
from hercules.blueprints.autoridades.models import Autoridad
from hercules.blueprints.edictos.models import Edicto
from hercules.extensions import database
from lib.safe_string import safe_clave, safe_string

load_dotenv()
SALT = os.environ.get("SALT")
CLOUD_STORAGE_DEPOSITO_EDICTOS = os.environ.get("CLOUD_STORAGE_DEPOSITO_EDICTOS")

app = create_app()
app.app_context().push()
database.app = app


@click.group()
def cli():
    """Edictos"""


@click.command()
@click.option("--clave", default="", type=str, help="Clave de la autoridad")
@click.option("--probar", is_flag=True, help="Probar sin cambiar la BD")
@click.option("--eliminar", is_flag=True, help="CUIDADO: Eliminar (A->B si NO hay archivo en GCS)")
@click.option("--eliminar-recuperar", is_flag=True, help="CUIDADO: Eliminar y recuperar (B->A si hay archivo en GCS)")
def refrescar(clave, probar, eliminar, eliminar_recuperar):
    """Refrescar la tabla edictos con los archivos en GCStorage"""

    # Si eliminar_recuperar es verdadero, siempre limpiar será verdadero
    if eliminar_recuperar is True:
        eliminar = True

    # Validar que exista el depósito
    try:
        bucket = storage.Client().get_bucket(CLOUD_STORAGE_DEPOSITO_EDICTOS)
    except NotFound as error:
        click.echo(click.style(f"No existe el depósito {CLOUD_STORAGE_DEPOSITO_EDICTOS}", fg="red"))
        sys.exit(1)

    # Preparar expresión regular para "NO" letras y digitos
    letras_digitos_regex = re.compile("[^0-9a-zA-Z]+")

    # Preparar expresión regular para hashid
    hashid_regexp = re.compile("[0-9a-zA-Z]{8}")

    # Para descifrar los hash ids
    hashids = Hashids(salt=SALT, min_length=8)

    # Para validar la fecha
    anos_limite = 20
    hoy = date.today()
    hoy_dt = datetime(year=hoy.year, month=hoy.month, day=hoy.day)
    limite_dt = datetime(year=hoy.year - anos_limite, month=1, day=1)

    # Inicializar contadores
    contador_incorrectos = 0
    contador_insertados = 0
    contador_presentes = 0
    contador_recuperados = 0
    contador_eliminados = 0

    # Inicializar listado de autoridades
    autoridades = []

    # Si viene la autoridad, validar
    autoridad = None
    if clave != "":
        clave = safe_clave(clave)
        autoridad = Autoridad.query.filter_by(clave=clave).first()
        if not autoridad:
            click.echo(click.style(f"No existe la autoridad con clave {clave}", fg="red"))
            sys.exit(1)
        if autoridad.estatus != "A":
            click.echo(click.style(f"La autoridad con clave {clave} está eliminada", fg="red"))
            sys.exit(1)
        autoridades = [autoridad]

    # Si NO hay filtro por autoridad, consultar TODAS las autoridades jurisdiccionales
    if autoridad is None:
        autoridades = (
            Autoridad.query.filter(Autoridad.es_jurisdiccional == True)
            .filter(Autoridad.estatus == "A")
            .order_by(Autoridad.clave)
            .all()
        )
        if len(autoridades) == 0:
            click.echo(click.style("No hay autoridades jurisdiccionales", fg="red"))
            sys.exit(1)
        click.echo(f"Encontré {len(autoridades)} autoridades jurisdiccionales")

    #
    # Bucle por autoridades
    #
    for autoridad in autoridades:
        # Consultar los edictos (activos e inactivos) de la autoridad
        edictos = Edicto.query.filter(Edicto.autoridad == autoridad).all()

        # Buscar los archivos en el subdirectorio
        subdirectorio = autoridad.directorio_edictos
        if subdirectorio == "":
            click.echo(click.style(f"Se omite {autoridad.clave} porque no tiene subdirectorio para edictos", fg="yellow"))
            continue
        blobs = list(bucket.list_blobs(prefix=subdirectorio))
        archivos_cantidad = len(blobs)
        if archivos_cantidad == 0:
            click.echo(click.style(f"No hay archivos en el subdirectorio {subdirectorio} para insertar", fg="yellow"))

        #
        # Bucle por los archivos en el depósito para insertar nuevos edictos
        #
        if archivos_cantidad > 0:
            click.echo(f"Tomando {archivos_cantidad} edictos en el subdirectorio {subdirectorio} para insertar: ", nl=False)
            for blob in blobs:
                # Saltar si no es un archivo PDF
                ruta = Path(blob.name)
                if ruta.suffix.lower() != ".pdf":
                    click.echo(click.style("[Bad pdf]", fg="red"))
                    contador_incorrectos += 1
                    continue

                # Saltar y quitar de la lista de edictos si se encuentra
                esta_en_bd = False
                for indice, edicto in enumerate(edictos):
                    if blob.public_url == edicto.url:
                        edictos.pop(indice)
                        esta_en_bd = True
                        break
                if esta_en_bd:
                    contador_presentes += 1
                    click.echo(click.style(".", fg="blue"), nl=False)
                    continue

                # A partir de aquí tenemos un archivo NUEVO que NO está en la base de datos
                # El nombre del archivo para un edicto debe ser como
                # AAAA-MM-DD-EEEE-EEEE-NUMP-NUMP-DESCRIPCION-BLA-BLA-IDHASED.pdf

                # Separar elementos del nombre del archivo
                nombre_sin_extension = ruta.name[:-4]
                elementos = re.sub(letras_digitos_regex, "-", nombre_sin_extension).strip("-").split("-")

                # Tomar la fecha
                try:
                    ano = int(elementos.pop(0))
                    mes = int(elementos.pop(0))
                    dia = int(elementos.pop(0))
                    fecha = date(ano, mes, dia)
                except (IndexError, ValueError):
                    click.echo(click.style("[Bad date]", fg="red"), nl=False)
                    contador_incorrectos += 1
                    continue

                # Descartar fechas en el futuro o muy en el pasado
                if not limite_dt <= datetime(year=fecha.year, month=fecha.month, day=fecha.day) <= hoy_dt:
                    click.echo(click.style("[Out of range]", fg="red"), nl=False)
                    contador_incorrectos += 1
                    continue

                # Tomar el expediente
                try:
                    numero = int(elementos[0])
                    ano = int(elementos[1])
                    expediente = str(numero) + "/" + str(ano)
                    elementos.pop(0)
                    elementos.pop(0)
                except (IndexError, ValueError):
                    expediente = ""

                # Tomar el número publicación
                try:
                    numero = int(elementos[0])
                    ano = int(elementos[1])
                    numero_publicacion = str(numero) + "/" + str(ano)
                    elementos.pop(0)
                    elementos.pop(0)
                except (IndexError, ValueError):
                    numero_publicacion = ""

                # Tomar la descripción, sin el hash del id de estar presente
                if len(elementos) > 1:
                    if re.match(hashid_regexp, elementos[-1]) is None:
                        descripcion = safe_string(" ".join(elementos))
                    else:
                        decodificado = hashids.decode(elementos[-1])
                        if isinstance(decodificado, tuple) and len(decodificado) > 0:
                            descripcion = safe_string(" ".join(elementos[:-1]))
                        else:
                            descripcion = safe_string(" ".join(elementos))
                else:
                    descripcion = "SIN DESCRIPCION"

                # Insertar EL EDICTO
                if probar is False:
                    tiempo_local = blob.time_created.astimezone(tzlocal())
                    Edicto(
                        creado=tiempo_local,
                        modificado=tiempo_local,
                        autoridad=autoridad,
                        fecha=fecha,
                        descripcion=descripcion,
                        expediente=expediente,
                        numero_publicacion=numero_publicacion,
                        archivo=ruta.name,
                        url=blob.public_url,
                    ).save()
                click.echo(click.style("+", fg="green"), nl=False)
                contador_insertados += 1

            # Poner avance de linea
            click.echo()

        # Si NO hay que limpiar, continuar
        if (eliminar is False) and (eliminar_recuperar is False):
            continue

        #
        # Bucle por los edictos restantes que se van a buscar por su URL
        #
        if len(edictos) > 0:
            click.echo(f"Buscando {len(edictos)} edictos de {autoridad.clave} para cambiar su estatus: ", nl=False)
            for edicto in edictos:
                # Validar el URL
                if edicto.url == "":
                    click.echo(click.style("[Empty URL]", fg="red"), nl=False)
                    contador_incorrectos += 1
                    if probar is False:
                        edicto.estatus = "B"
                        edicto.save()
                    continue

                # Obtener el archivo en el depósito a partir del URL
                parsed_url = urlparse(edicto.url)
                try:
                    blob_name_complete = parsed_url.path[1:]  # Extract path and remove the first slash
                    blob_name = "/".join(blob_name_complete.split("/")[1:])  # Remove first directory, it's the bucket name
                except IndexError as error:
                    click.echo(click.style("[Bad URL]", fg="red"), nl=False)
                    if probar is False:
                        edicto.estatus = "B"
                        edicto.save()
                    contador_incorrectos += 1
                    continue
                blob = bucket.get_blob(unquote(blob_name))  # Get the file

                # Si NO existe el archivo y está en estatus A, se elimina
                if eliminar is True and blob is None and edicto.estatus == "A":
                    if probar is False:
                        edicto.estatus = "B"
                        edicto.save()
                    click.echo(click.style("B", fg="yellow"), nl=False)
                    contador_eliminados += 1
                    continue

                # Si SI existe el archivo y está en estatus B, se recupera
                if eliminar_recuperar is True and blob and edicto.estatus == "B":
                    if probar is False:
                        edicto.estatus = "A"
                        edicto.save()
                    click.echo(click.style("A", fg="green"), nl=False)
                    contador_recuperados += 1
                    continue

                # No hay que cambiar nada
                click.echo(click.style(".", fg="blue"), nl=False)

    # Mensaje final
    click.echo()
    if probar is True:
        click.echo(click.style("Terminó en modo PROBAR: No hay cambios en la base de datos.", fg="white"))
    if contador_presentes > 0:
        click.echo(click.style(f"Se encontraron {contador_presentes} edictos", fg="green"))
    if contador_insertados > 0:
        click.echo(click.style(f"Se insertaron {contador_insertados} edictos", fg="green"))
    if contador_incorrectos > 0:
        click.echo(click.style(f"Hubo {contador_incorrectos} archivos incorrectos", fg="yellow"))
    if contador_recuperados > 0:
        click.echo(click.style(f"Se recuperaron {contador_recuperados} edictos (estatus cambio a A)", fg="green"))
    if contador_eliminados > 0:
        click.echo(click.style(f"Se eliminaron {contador_eliminados} edictos (estatus cambio a B)", fg="green"))


cli.add_command(refrescar)
