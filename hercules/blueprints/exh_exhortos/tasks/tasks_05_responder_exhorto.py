"""
Tareas en el fondo, Exh Exhortos 05 Responder exhorto
"""

from hercules.blueprints.exh_exhortos.tasks.tasks_00_bitacora import bitacora


def task_responder_exhorto(folio_seguimiento: str) -> tuple[str, str, str]:
    """Responder exhortos"""
    bitacora.info("Inicia responder exhorto")

    # Elaborar mensaje_termino
    mensaje_termino = f"Termina responder exhorto {folio_seguimiento}"
    bitacora.info(mensaje_termino)

    # Entregar mensaje_termino, nombre_archivo y url_publica
    return mensaje_termino, "", ""
