"""
Copiar
"""

import os
import sys

import click
import psycopg2
from dotenv import load_dotenv

load_dotenv()  # Take environment variables from .env


def copiar_tabla(tabla: str):
    """Copiar tabla de una base de datos a la que usamos"""

    # Definir los parametros de conexion a la base de datos de origen
    source_conn_params = {
        "dbname": os.environ.get("DB_SOURCE_NAME", ""),
        "user": os.environ.get("DB_SOURCE_USER", ""),
        "password": os.environ.get("DB_SOURCE_PASS", ""),
        "host": os.environ.get("DB_SOURCE_HOST", ""),
        "port": os.environ.get("DB_SOURCE_PORT", "5432"),
    }

    # Definir los parametros de conexion a la base de datos de destino
    destination_conn_params = {
        "dbname": os.environ.get("DB_NAME", ""),
        "user": os.environ.get("DB_USER", ""),
        "password": os.environ.get("DB_PASS", ""),
        "host": os.environ.get("DB_HOST", "127.0.0.1"),
        "port": os.environ.get("DB_PORT", "5432"),
    }

    # Conectar a las bases de datos
    try:
        click.echo("Conectando a la BD de origen... ", nl=False)
        source_conn = psycopg2.connect(**source_conn_params)
        click.echo(click.style("Conectado.", fg="green"))
        click.echo("Conectando a la BD de destino... ", nl=False)
        destination_conn = psycopg2.connect(**destination_conn_params)
        click.echo(click.style("Conectado.", fg="green"))
    except psycopg2.OperationalError as error:
        click.echo(f"Error al conectar a la base de datos: {error}")
        sys.exit(1)

    # Inicializar contador
    contador = 0

    # Copiar tabla
    click.echo(f"Copiando tabla {tabla}... ", nl=False)
    try:
        source_cursor = source_conn.cursor()
        destination_cursor = destination_conn.cursor()

        # Obtener los registros
        source_cursor.execute(f"SELECT * FROM {tabla}")
        rows = source_cursor.fetchall()

        # Definir los nombres de las columnas
        colnames = [desc[0] for desc in source_cursor.description]

        # Elaborar comandos SQL para insertar
        insert_query = f"INSERT INTO {tabla} ({', '.join(colnames)}) VALUES %s"

        # Insertar registros
        psycopg2.extras.execute_values(destination_cursor, insert_query, rows)

        # Ejecutar las operaciones
        destination_conn.commit()

        # Incrementar contador
        contador += len(rows)

        # Actualizar la secuencia al valor mas alto de la columna id
        destination_cursor.execute(
            f"""
            do $$
            declare nextid int;
            begin
                select max(id) + 1 from {tabla} into nextid;
                execute 'alter SEQUENCE {tabla}_id_seq RESTART with '|| nextid;
            end;
            $$ language plpgsql
        """
        )

        # Ejecutar la operacion
        destination_conn.commit()

    finally:
        source_cursor.close()
        destination_cursor.close()
        source_conn.close()
        destination_conn.close()

    # Mostrar el contador
    click.echo(f"Se copiaron {contador} registros.")
