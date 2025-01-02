"""
CLI Sentencias
"""

import os
import sys
from datetime import datetime
from pathlib import Path
from urllib.parse import unquote

import click
from dotenv import load_dotenv
from openai import OpenAI
from pypdf import PdfReader

from hercules.app import create_app
from hercules.blueprints.sentencias.models import Sentencia
from hercules.extensions import database

# Cargar variables de entorno
load_dotenv()
OPENAI_API_KEY = os.getenv("OPENAI_API_KEY", "NONE")
OPENAI_ENDPOINT = os.getenv("OPENAI_ENDPOINT", "http://127.0.0.1:11434/v1")
OPENAI_MODEL = os.getenv("OPENAI_MODEL", "")
OPENAI_ORG_ID = os.getenv("OPENAI_ORG_ID", "NONE")
OPENAI_PROJECT_ID = os.getenv("OPENAI_PROJECT_ID", "NONE")
OPENAI_PROMPT = os.getenv("OPENAI_PROMPT", "")
BASE_DIR = os.getenv("SENTENCIAS_BASE_DIR", "")
GCS_BASE_URL = os.getenv("SENTENCIAS_GCS_BASE_URL", "")

# Inicializar conexión con la base de datos
app = create_app()
app.app_context().push()
database.app = app


@click.group()
def cli():
    """Sentencias"""


@click.command()
@click.argument("prompt", type=str)
def probar_ollama(prompt):
    """Probar Ollama"""

    # Inicializar OpenAI
    open_ai = OpenAI(
        api_key=OPENAI_API_KEY,
        base_url=OPENAI_ENDPOINT,
        organization=OPENAI_ORG_ID,
        project=OPENAI_PROJECT_ID,
        timeout=60,
    )

    # Definir los mensajes que se va a enviar
    mensajes = []
    if OPENAI_PROMPT != "":
        mensajes.append({"role": "system", "content": OPENAI_PROMPT})
    mensajes.append({"role": "user", "content": prompt})

    # Enviar los mensajes
    try:
        response = open_ai.chat.completions.create(
            model=OPENAI_MODEL,
            messages=mensajes,
            stream=False,
        )
    except Exception as error:
        click.echo(click.style(str(error), fg="red"))
        sys.exit(1)

    # Mostrar respuesta
    print(response.choices[0].message.content)
    click.echo(click.style("Respuesta exitosa", fg="green"))


@click.command()
@click.argument("archivo", type=str)
def extraer_texto_de_un_archivo_pdf(archivo):
    """Extraer texto de un archivo PDF"""
    ruta = Path(archivo)
    if ruta.exists() is False or ruta.is_file() is False:
        click.echo(click.style("No existe el archivo", fg="red"))
        sys.exit(1)
    if ruta.suffix.lower() != ".pdf":
        click.echo(click.style("No es un archivo PDF", fg="red"))
        sys.exit(1)
    texto = ""
    try:
        lector = PdfReader(ruta)
        paginas_textos = []
        for pagina in lector.pages:
            texto_sin_avances_de_linea = pagina.extract_text().replace("\n", " ")
            paginas_textos.append(" ".join(texto_sin_avances_de_linea.split()))
        texto = " ".join(paginas_textos)
    except Exception as error:
        click.echo(click.style(str(error), fg="red"))
    click.echo(texto)


@click.command()
@click.argument("fecha", type=str)
@click.option("--sobreescribir", is_flag=True)
def sintetizar(fecha, sobreescribir):
    """Extraer texto de sentencias de una fecha dada"""

    # Validar la fecha
    try:
        fecha = datetime.strptime(fecha, "%Y-%m-%d").date()
    except ValueError as error:
        click.echo(click.style("La fecha es invalida", fg="red"))

    # Validar que exista el directorio SENTENCIAS_BASE_DIR
    sentencias_dir = Path(BASE_DIR)
    if sentencias_dir.exists() is False or sentencias_dir.is_dir() is False:
        click.echo(click.style(f"No existe el directorio {BASE_DIR}", fg="red"))
        sys.exit(1)

    # Validar el prompt
    if OPENAI_PROMPT == "":
        click.echo(click.style(f"No esta definido OPENAI_PROMPT", fg="red"))
        sys.exit(1)

    # Inicializar OpenAI
    open_ai = OpenAI(
        api_key=OPENAI_API_KEY,
        base_url=OPENAI_ENDPOINT,
        organization=OPENAI_ORG_ID,
        project=OPENAI_PROJECT_ID,
        timeout=60,
    )

    # Consultar las sentencias
    sentencias = Sentencia.query.filter(Sentencia.fecha == fecha).filter(Sentencia.estatus == "A").order_by(Sentencia.id)
    if sentencias.count() == 0:
        click.echo(click.style(f"No hay sentencias en la fecha {fecha}", fg="red"))
        sys.exit(1)

    # Bucle por las sentencias
    for sentencia in sentencias.all():
        click.echo(click.style(f"[{sentencia.id}] ", fg="white"), nl=False)

        # Si la sentencia ya fue analizada, se omite
        if sobreescribir is False and sentencia.rag_fue_analizado_tiempo is not None:
            click.echo(click.style("Se va omitir porque ya fue analizada", fg="yellow"))
            continue

        # Definir la ruta al archivo pdf reemplazando el inicio del url con el directorio
        archivo_ruta = Path(BASE_DIR + unquote(sentencia.url[len(GCS_BASE_URL) :]))

        # Verificar que exista el archivo pdf
        archivo_ruta_existe = bool(archivo_ruta.exists() and archivo_ruta.is_file())

        # Mostrar el nombre del archivo en verde
        if archivo_ruta_existe is True:
            click.echo(click.style(f"{archivo_ruta.name} ", fg="green"), nl=False)
        else:
            click.echo(click.style(sentencia.archivo, fg="white"), nl=False)
            click.echo(click.style("No existe y se va omitir", fg="yellow"), nl=False)
            continue

        # Validar que el archivo sea PDF
        if archivo_ruta.suffix.lower() != ".pdf":
            click.echo(click.style("No es un archivo PDF", fg="yellow"))
            continue

        # Extraer el texto
        texto = ""
        try:
            lector = PdfReader(archivo_ruta)
            paginas_textos = []
            for pagina in lector.pages:
                texto_sin_avances_de_linea = pagina.extract_text().replace("\n", " ")
                paginas_textos.append(" ".join(texto_sin_avances_de_linea.split()))
            texto = " ".join(paginas_textos)
        except Exception as error:
            click.echo(click.style("Error al extraer: " + str(error), fg="yellow"))
            continue

        # Si no hay texto, omitir
        if texto == "":
            click.echo(click.style("No hay texto", fg="yellow"))
            continue

        # Mostrar los primeros 48 caracteres del texto
        click.echo(click.style(texto[:48] + ", ", fg="white"), nl=False)

        # Definir los datos del análisis
        rag_analisis = {
            "archivo_tamanio": archivo_ruta.stat().st_size,
            "autor": sentencia.autoridad.clave,
            "longitud": len(texto),
            "texto": texto,
        }

        # Actualizar en la base de datos
        sentencia.rag_analisis = rag_analisis
        sentencia.rag_fue_analizado_tiempo = datetime.now()
        sentencia.save()

        # Mostrar que se ha guardado
        click.echo(click.style(f"Analizado ({rag_analisis['longitud']}) ", fg="green"), nl=False)

        # Si la sentencia ya fue sintetizada, se omite
        if sobreescribir is False and sentencia.rag_fue_sintetizado_tiempo is not None:
            click.echo(click.style(" se va omitir porque ya fue sintetizada", fg="yellow"))
            continue

        # Definir los mensajes a enviar
        mensajes = [
            {"role": "system", "content": OPENAI_PROMPT},
            {"role": "user", "content": texto},
        ]

        # Enviar a OpenAI el texto
        try:
            chat_response = open_ai.chat.completions.create(
                model=OPENAI_MODEL,
                messages=mensajes,
                stream=False,
            )
        except Exception as error:
            click.echo(click.style("Error al sintetizar: " + str(error), fg="yellow"))
            continue

        # Definir los datos de la síntesis
        rag_sintesis = {
            "modelo": chat_response.model,
            "sintesis": chat_response.choices[0].message.content,
            "tokens_total": chat_response.usage.total_tokens,
        }

        # Actualizar en la base de datos
        sentencia.rag_sintesis = rag_sintesis
        sentencia.rag_fue_sintetizado_tiempo = datetime.now()
        sentencia.save()

        # Mostrar que se ha guardado
        click.echo(click.style(f"Sintetizado ({rag_sintesis['tokens_total']}) ", fg="magenta"), nl=False)
        click.echo()


cli.add_command(probar_ollama)
cli.add_command(extraer_texto_de_un_archivo_pdf)
cli.add_command(sintetizar)
