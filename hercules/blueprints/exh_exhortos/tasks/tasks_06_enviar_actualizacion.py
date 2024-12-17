"""
Tareas en el fondo, Exh Exhortos 06 Enviar Actualización
"""

from hercules.blueprints.exh_exhortos.tasks.tasks_00_bitacora import bitacora


def task_enviar_actualizacion(exhorto_origen_id: str) -> tuple[str, str, str]:
    """Enviar actualización"""
    bitacora.info("Inicia enviar actualización")

    # Elaborar mensaje_termino
    mensaje_termino = f"Termina enviar actualización {exhorto_origen_id}"
    bitacora.info(mensaje_termino)

    # Entregar mensaje_termino, nombre_archivo y url_publica
    return mensaje_termino, "", ""
