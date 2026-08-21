"""
Arc Archivos

- pasar_al_historial: Pasa al historial las solicitudes entregadas y las remesas procesadas después de varios días.
"""

import click

from hercules.app import create_app
from hercules.extensions import database

app = create_app()
app.app_context().push()
database.app = app


@click.group()
def cli():
    """Arc Archivos"""


@click.command()
def pasar_al_historial():
    """Pasar al historial las solicitudes y remesas con mucha antigüedad habiendo sido procesadas correctamente"""

    app.task_queue.enqueue(
        "can_mayor.blueprints.arc_archivos.tasks.pasar_al_historial_solicitudes_completadas",
    )
    click.echo("Pasar al historial las solicitudes atendidas.")

    app.task_queue.enqueue(
        "can_mayor.blueprints.arc_archivos.tasks.pasar_al_historial_solicitudes_canceladas",
    )
    click.echo("Pasar al historial las solicitudes canceladas.")

    app.task_queue.enqueue(
        "can_mayor.blueprints.arc_archivos.tasks.pasar_al_historial_remesas_archivadas",
    )
    click.echo("Pasar al historial las remesas archivadas.")

    app.task_queue.enqueue(
        "can_mayor.blueprints.arc_archivos.tasks.pasar_al_historial_remesas_canceladas",
    )
    click.echo("Pasar al historial las remesas canceladas.")

    app.task_queue.enqueue(
        "can_mayor.blueprints.arc_archivos.tasks.pasar_al_historial_remesas_rechazadas",
    )
    click.echo("Pasar al historial las remesas rechazadas.")


cli.add_command(pasar_al_historial)
