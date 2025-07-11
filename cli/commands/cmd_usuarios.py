"""
CLI Usuarios

- generar_fernet_key: Generar FERNET_KEY
- mostrar_api_key: Mostrar la API Key
- mostrar_efirma_contrasena: Mostrar la contraseña de efirma
- nueva_api_key: Nueva API Key
- nueva_contrasena: Nueva contraseña que se guarda con cifrado asimétrico
- nueva_efirma_contrasena: Nueva efirma contraseña que se guarda con cifrado simétrico
- reporte: Reporte de usuarios modificados a un archivo CSV
"""

import csv
import calendar
from datetime import datetime, timedelta
from pathlib import Path
import os
import re
import sys

import click
from dotenv import load_dotenv

from hercules.app import create_app
from hercules.blueprints.usuarios.models import Usuario
from hercules.extensions import database, pwd_context
from lib.cryptography import convert_string_to_fernet_key, simmetric_crypt, simmetric_decrypt
from lib.pwgen import generar_api_key

# Cargar variables de entorno
load_dotenv()
FERNET_KEY = os.getenv("FERNET_KEY", "")
SALT = os.getenv("SALT", "")

# Cargar la app de Hercules para usar SQLAlchemy ORMs
app = create_app()
app.app_context().push()
# database.app = app


@click.group()
def cli():
    """Usuarios"""


@click.command()
@click.argument("frase", type=str)
def generar_fernet_key(frase):
    """Generar FERNET_KEY"""
    if not frase:
        click.echo("ERROR: Debes proporcionar una frase para generar la clave Fernet.")
        sys.exit(1)
    if not SALT:
        click.echo("ERROR: La variable de entorno SALT no está definida.")
        sys.exit(1)
    fernet_key = convert_string_to_fernet_key(frase, SALT)
    click.echo(f"FERNET_KEY={fernet_key.decode('utf-8')}")
    click.echo("Guarda esta clave en tu archivo .env como FERNET_KEY.")


@click.command()
@click.argument("email", type=str)
def mostrar_api_key(email):
    """Mostrar la API Key"""
    usuario = Usuario.query.filter_by(email=email).first()
    if usuario is None:
        click.echo(f"ERROR: No existe el e-mail {email} en usuarios")
        sys.exit(1)
    click.echo(f"Usuario: {usuario.email}")
    click.echo(f"API key: {usuario.api_key}")
    click.echo(f"Expira:  {usuario.api_key_expiracion.strftime('%Y-%m-%d')}")


@click.command()
@click.argument("email", type=str)
def mostrar_efirma_contrasena(email):
    """Mostrar la contraseña de efirma"""
    usuario = Usuario.query.filter_by(email=email).first()
    if usuario is None:
        click.echo(f"ERROR: No existe el e-mail {email} en usuarios")
        sys.exit(1)
    if not usuario.efirma_contrasena:
        click.echo(f"ERROR: El usuario {email} no tiene una contraseña de efirma definida.")
        sys.exit(1)
    click.echo(f"Usuario: {usuario.email} - {usuario.nombre} - {usuario.puesto}")
    if not FERNET_KEY:
        click.echo("ERROR: FERNET_KEY no está definida en las variables de entorno.")
        sys.exit(1)
    try:
        efirma_contrasena = simmetric_decrypt(usuario.efirma_contrasena, FERNET_KEY)
    except Exception as error:
        raise error
        click.echo(f"ERROR: No se pudo descifrar la contraseña de efirma: {error}")
        sys.exit(1)
    click.echo(f"Contraseña de efirma: {efirma_contrasena}")


@click.command()
@click.argument("email", type=str)
@click.option("--dias", default=90, help="Cantidad de días para expirar la API Key")
def nueva_api_key(email, dias):
    """Nueva API Key"""
    usuario = Usuario.find_by_identity(email)
    if usuario is None:
        click.echo(f"No existe el e-mail {email} en usuarios")
        return
    api_key = generar_api_key(usuario.id, usuario.email)
    api_key_expiracion = datetime.now() + timedelta(days=dias)
    usuario.api_key = api_key
    usuario.api_key_expiracion = api_key_expiracion
    usuario.save()
    click.echo("Nueva API key")
    click.echo(f"Usuario: {usuario.email}")
    click.echo(f"API key: {usuario.api_key}")
    click.echo(f"Expira:  {usuario.api_key_expiracion.strftime('%Y-%m-%d')}")


@click.command()
@click.argument("email", type=str)
def nueva_contrasena(email):
    """Nueva contraseña que se guarda con cifrado asimétrico"""
    usuario = Usuario.query.filter_by(email=email).first()
    if usuario is None:
        click.echo(f"ERROR: No existe el e-mail {email} en usuarios")
        sys.exit(1)
    contrasena_1 = input("Contraseña: ")
    contrasena_2 = input("De nuevo la misma contraseña: ")
    if contrasena_1 != contrasena_2:
        click.echo("ERROR: No son iguales las contraseñas. Por favor intente de nuevo.")
        sys.exit(1)
    usuario.contrasena = pwd_context.hash(contrasena_1.strip())
    usuario.save()
    click.echo(f"Se ha cambiado la contraseña de {email} en usuarios")


@click.command()
@click.argument("email", type=str)
def nueva_efirma_contrasena(email):
    """Nueva efirma contraseña que se guarda con cifrado simétrico"""
    usuario = Usuario.query.filter_by(email=email).first()
    if usuario is None:
        click.echo(f"ERROR: No existe el e-mail {email} en usuarios")
        sys.exit(1)
    click.echo(f"Usuario: {usuario.email} - {usuario.nombre} - {usuario.puesto}")
    if not FERNET_KEY:
        click.echo("ERROR: FERNET_KEY no está definida en las variables de entorno.")
        sys.exit(1)
    efirma_contrasena = input("Contraseña de efirma: ").strip()
    if not efirma_contrasena:
        click.echo("ERROR: La contraseña de efirma no puede estar vacía.")
        sys.exit(1)
    try:
        efirma_contrasena_cifrada = simmetric_crypt(efirma_contrasena, FERNET_KEY)
    except Exception as error:
        click.echo(f"ERROR: No se pudo cifrar la contraseña de efirma: {error}")
        sys.exit(1)
    usuario.efirma_contrasena = efirma_contrasena_cifrada
    usuario.save()
    click.echo(f"Se ha cambiado la contraseña de efirma de {email} en usuarios")


@click.command()
@click.argument("anio_mes", type=str)
@click.option("--output", default="reporte_usuarios.csv", type=str, help="Archivo CSV a escribir")
def generar_sicgd_csv(anio_mes, output):
    """Generar CSV para SICGD Usuarios en el Sistema de Plataforma Web"""
    # Validar el archivo CSV a escribir, que no exista
    ruta = Path(output)
    if ruta.exists():
        click.echo(f"AVISO: {output} existe, no voy a sobreescribirlo.")
        return
    # Validar que el parámetro mes_int sea YYYY-MM
    if not re.match(r"^\d{4}-\d{2}$", anio_mes):
        click.echo(f"ERROR: {anio_mes} no es una fecha valida (YYYY-MM)")
        return
    # Calcular fecha desde y hasta
    desde = f"{anio_mes}-01"
    anio = int(anio_mes[0:4])
    mes = int(anio_mes[5:7])
    _, ultimo_dia = calendar.monthrange(anio, mes)
    hasta = f"{anio_mes}-{ultimo_dia}"
    # Validar que la fecha desde sea menor que la fecha hasta
    if desde > hasta:
        click.echo(f"ERROR: {desde} es mayor que {hasta}")
        return
    # Consultar usuarios
    click.echo("Elaborando reporte de usuarios...")
    contador = 0
    usuarios = Usuario.query
    if desde:
        usuarios = usuarios.filter(Usuario.modificado >= f"{desde} 00:00:00")
    if hasta:
        usuarios = usuarios.filter(Usuario.modificado <= f"{hasta} 23:59:59")
    usuarios = usuarios.order_by(Usuario.modificado).all()
    with open(ruta, "w", encoding="utf8") as puntero:
        respaldo = csv.writer(puntero)
        respaldo.writerow(
            [
                "Fecha",
                "Nombre Completo",
                "CURP",
                "Correo Electrónico",
                "Autoridad",
                "Oficina",
                "Roles",
                "Operacion",
            ]
        )
        for usuario in usuarios:
            # Definir operacion
            operacion = "ALTA"  # Por defecto, es ALTA
            if usuario.estatus == "B":
                operacion = "BAJA"  # Si estatus es B, es BAJA
            elif usuario.modificado - usuario.creado > timedelta(hours=24):
                operacion = "CAMBIO"  # Si modificado tiene mas de 24 horas respecto a creado, es CAMBIO
            # Escribir la linea
            respaldo.writerow(
                [
                    usuario.modificado.strftime("%Y-%m-%d %H:%M:%S"),
                    usuario.nombre,
                    usuario.curp,
                    usuario.email,
                    usuario.autoridad.clave,
                    usuario.oficina.clave,
                    ", ".join(usuario.get_roles()),
                    operacion,
                ]
            )
            contador += 1
            if contador % 100 == 0:
                click.echo(f"  Van {contador}...")
    click.echo(f"  {contador} en {ruta.name}")


cli.add_command(generar_fernet_key)
cli.add_command(mostrar_api_key)
cli.add_command(mostrar_efirma_contrasena)
cli.add_command(nueva_api_key)
cli.add_command(nueva_contrasena)
cli.add_command(nueva_efirma_contrasena)
cli.add_command(generar_sicgd_csv)
