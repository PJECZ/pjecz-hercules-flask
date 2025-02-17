"""
Communications, Enviar Exhorto
"""

from hercules.blueprints.exh_exhortos.communications import bitacora


def enviar_exhorto(exh_exhorto_id: int) -> tuple[str, str, str]:
    """Enviar exhorto"""
    bitacora.info("Inicia enviar el exhorto al PJ externo.")

    # Elaborar mensaje final
    mensaje_termino = f"Termina enviar el exhorto con ID {exh_exhorto_id} al PJ externo."
    bitacora.info(mensaje_termino)

    # Entregar mensaje_termino, nombre_archivo y url_publica
    return mensaje_termino, "", ""
