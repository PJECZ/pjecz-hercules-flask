"""
Tareas en el fondo, Exh Exhortos 07 Enviar Promoción
"""

from hercules.blueprints.exh_exhortos.tasks.tasks_00_bitacora import bitacora


def task_enviar_promocion(exhorto_origen_id: str) -> tuple[str, str, str]:
    """Enviar promoción"""
    bitacora.info("Inicia enviar promoción")

    # Elaborar mensaje_termino
    mensaje_termino = f"Termina enviar promoción {exhorto_origen_id}"
    bitacora.info(mensaje_termino)

    # Entregar mensaje_termino, nombre_archivo y url_publica
    return mensaje_termino, "", ""
