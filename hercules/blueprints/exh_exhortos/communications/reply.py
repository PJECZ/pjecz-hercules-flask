"""
Communications, Responder Exhorto
"""

from hercules.blueprints.exh_exhortos.communications import bitacora


def responder_exhorto(exh_exhorto_id: int) -> tuple[str, str, str]:
    """Responder exhortos"""
    bitacora.info("Inicia responder exhorto al PJ externo.")

    # Elaborar mensaje_termino
    mensaje_termino = "Termina responder exhorto al PJ externo."
    bitacora.info(mensaje_termino)

    # Entregar mensaje_termino, nombre_archivo y url_publica
    return mensaje_termino, "", ""
