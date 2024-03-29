"""
CLI Google AI Studio
"""

import os

import click
from dotenv import load_dotenv

import google.generativeai as genai

load_dotenv()

AI_STUDIO_API_KEY = os.getenv("AI_STUDIO_API_KEY", "")


@click.group()
def cli():
    """Google AI Studio"""


@cli.command()
def listar_modelos():
    """Listar modelos"""
    click.echo("Listar modelos AI Studio")

    genai.configure(api_key=AI_STUDIO_API_KEY)
    for m in genai.list_models():
        if "generateContent" in m.supported_generation_methods:
            print(m.name)

    click.echo()


@cli.command()
@click.argument("input_text", type=str)
def preguntar(input_text):
    """Preguntar"""
    click.echo("Preguntar a AI Studio")

    genai.configure(api_key=AI_STUDIO_API_KEY)
    model = genai.GenerativeModel("gemini-1.0-pro")
    response = model.generate_content(input_text)
    click.echo(response.text)


cli.add_command(listar_modelos)
cli.add_command(preguntar)
