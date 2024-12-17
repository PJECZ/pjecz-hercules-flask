"""
Tareas en el fondo, Exh Exhortos 04 consultar exhorto
"""

from hercules.blueprints.exh_exhortos.tasks.tasks_00_bitacora import bitacora


def task_consultar_exhorto(folio_seguimiento: str = "") -> tuple[str, str, str]:
    """Consultar exhortos"""
    bitacora.info("Inicia consultar exhorto")

    # Elaborar mensaje_termino
    mensaje_termino = f"Termina consultar exhorto {folio_seguimiento}"
    bitacora.info(mensaje_termino)

    # Entregar mensaje_termino, nombre_archivo y url_publica
    return mensaje_termino, "", ""
