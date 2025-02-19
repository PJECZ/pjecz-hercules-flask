"""
CLI Exh Exhortos
"""

import click

from cli.commands.exh_exhortos_demo_02_enviar_exhorto import demo_enviar_exhorto
from cli.commands.exh_exhortos_demo_02_recibir_exhorto import demo_recibir_exhorto
from cli.commands.exh_exhortos_demo_05_enviar_respuesta import demo_enviar_respuesta
from cli.commands.exh_exhortos_demo_05_recibir_respuesta import demo_recibir_respuesta
from cli.commands.exh_exhortos_demo_06_enviar_actualizacion import demo_enviar_actualizacion
from cli.commands.exh_exhortos_demo_06_recibir_actualizacion import demo_recibir_actualizacion
from cli.commands.exh_exhortos_demo_07_enviar_promocion import demo_enviar_promocion
from cli.commands.exh_exhortos_demo_07_recibir_promocion import demo_recibir_promocion
from cli.commands.exh_exhortos_truncar import truncar as ejecutar_truncar
from hercules.blueprints.exh_exhortos.tasks.tasks_02_enviar_exhorto import task_enviar_exhorto
from hercules.blueprints.exh_exhortos.tasks.tasks_04_consultar_exhorto import task_consultar_exhorto
from hercules.blueprints.exh_exhortos.tasks.tasks_05_responder_exhorto import task_responder_exhorto
from hercules.blueprints.exh_exhortos.tasks.tasks_06_enviar_actualizacion import task_enviar_actualizacion
from hercules.blueprints.exh_exhortos.tasks.tasks_07_enviar_promocion import task_enviar_promocion


@click.group()
def cli():
    """Exh Exhortos"""


@click.command()
@click.argument("exhorto_origen_id", type=str)
def demo_02_enviar(exhorto_origen_id):
    """DEMO Enviar un exhorto"""
    click.echo("DEMO Enviar un exhorto PENDIENTE o POR ENVIAR")
    mensaje = demo_enviar_exhorto(exhorto_origen_id)
    click.echo(click.style(mensaje, fg="green"))


@click.command()
@click.argument("estado_origen", type=str)
def demo_02_recibir(estado_origen):
    """DEMO Recibir un exhorto"""
    click.echo("DEMO Recibir un exhorto")
    mensaje = demo_recibir_exhorto(estado_origen)
    click.echo(click.style(mensaje, fg="green"))


@click.command()
@click.argument("exhorto_origen_id", type=str)
def demo_05_enviar_respuesta(exhorto_origen_id):
    """DEMO Responder un exhorto"""
    click.echo("DEMO Responder un exhorto PROCESANDO o DILIGENCIADO")
    mensaje = demo_enviar_respuesta(exhorto_origen_id)
    click.echo(click.style(mensaje, fg="green"))


@click.command()
@click.argument("exhorto_origen_id", type=str)
def demo_05_recibir_respuesta(exhorto_origen_id):
    """DEMO Recibir la respuesta de un exhorto"""
    click.echo("DEMO Recibir respuesta de un exhorto RECIBIDO CON EXITO")
    mensaje = demo_recibir_respuesta(exhorto_origen_id)
    click.echo(click.style(mensaje, fg="green"))


@click.command()
@click.argument("exhorto_origen_id", type=str)
@click.argument("actualizacion_origen_id", type=str)
def demo_06_enviar_actualizacion(exhorto_origen_id, actualizacion_origen_id):
    """DEMO Enviar una actualización"""
    click.echo("DEMO Enviar una actualización")
    mensaje = demo_enviar_actualizacion(exhorto_origen_id, actualizacion_origen_id)
    click.echo(click.style(mensaje, fg="green"))


@click.command()
@click.argument("exhorto_origen_id", type=str)
def demo_06_recibir_actualizacion(exhorto_origen_id):
    """DEMO Recibir una actualización"""
    click.echo("DEMO Recibir una actualización")
    mensaje = demo_recibir_actualizacion(exhorto_origen_id)
    click.echo(click.style(mensaje, fg="green"))


@click.command()
@click.argument("exhorto_origen_id", type=str)
@click.argument("folio_origen_promocion", type=str)
def demo_07_enviar_promocion(exhorto_origen_id, folio_origen_promocion):
    """DEMO Enviar una promoción"""
    click.echo("DEMO Enviar una promoción")
    mensaje = demo_enviar_promocion(exhorto_origen_id, folio_origen_promocion)
    click.echo(click.style(mensaje, fg="green"))


@click.command()
@click.argument("exhorto_origen_id", type=str)
def demo_07_recibir_promocion(exhorto_origen_id):
    """DEMO Recibir una promoción"""
    click.echo("DEMO Recibir una promoción")
    mensaje = demo_recibir_promocion(exhorto_origen_id)
    click.echo(click.style(mensaje, fg="green"))


@click.command()
@click.argument("exhorto_origen_id", type=str)
def task_02_enviar_exhorto(exhorto_origen_id):
    """Enviar un exhorto"""
    click.echo("Enviar un exhorto")
    mensaje, _, _ = task_enviar_exhorto(exhorto_origen_id)
    click.echo(click.style(mensaje, fg="green"))


@click.command()
@click.argument("folio_seguimiento", type=str)
def task_04_consultar_exhorto(folio_seguimiento):
    """Consultar un exhorto"""
    click.echo("Consultar un exhorto")
    mensaje, _, _ = task_consultar_exhorto(folio_seguimiento)
    click.echo(click.style(mensaje, fg="green"))


@click.command()
@click.argument("folio_seguimiento", type=str)
def task_05_responder_exhorto(folio_seguimiento):
    """Responder un exhorto"""
    click.echo("Responder un exhorto")
    mensaje, _, _ = task_responder_exhorto(folio_seguimiento)
    click.echo(click.style(mensaje, fg="green"))


@click.command()
@click.argument("exhorto_origen_id", type=str)
def task_06_enviar_actualizacion(exhorto_origen_id):
    """Enviar una actualización"""
    click.echo("Enviar una actualización")
    mensaje, _, _ = task_enviar_actualizacion(exhorto_origen_id)
    click.echo(click.style(mensaje, fg="green"))


@click.command()
@click.argument("exhorto_origen_id", type=str)
def task_07_enviar_promocion(exhorto_origen_id):
    """Enviar una promoción"""
    click.echo("Enviar una promoción")
    mensaje, _, _ = task_enviar_promocion(exhorto_origen_id)
    click.echo(click.style(mensaje, fg="green"))


@click.command()
def truncar():
    """Truncar la tabla de exhortos y sus tablas relacionadas"""
    click.echo("Truncar la tabla de exhortos y sus tablas relacionadas")
    mensaje = ejecutar_truncar()
    click.echo(click.style(mensaje, fg="green"))


cli.add_command(demo_02_enviar)
cli.add_command(demo_02_recibir)
cli.add_command(demo_05_enviar_respuesta)
cli.add_command(demo_05_recibir_respuesta)
cli.add_command(demo_06_enviar_actualizacion)
cli.add_command(demo_06_recibir_actualizacion)
cli.add_command(demo_07_enviar_promocion)
cli.add_command(demo_07_recibir_promocion)
cli.add_command(task_02_enviar_exhorto)
cli.add_command(task_04_consultar_exhorto)
cli.add_command(task_05_responder_exhorto)
cli.add_command(task_06_enviar_actualizacion)
cli.add_command(task_07_enviar_promocion)
cli.add_command(truncar)
