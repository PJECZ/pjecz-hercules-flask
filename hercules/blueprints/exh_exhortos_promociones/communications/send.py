"""
Communications, Enviar Promocion
"""

from hercules.blueprints.exh_exhortos.communications import bitacora


def enviar_promocion(exh_exhorto_promocion_id: int) -> tuple[str, str, str]:
    """Enviar promoción"""
    bitacora.info("Inicia enviar promoción")

    # Elaborar mensaje_termino
    mensaje_termino = f"Termina enviar promoción {exh_exhorto_promocion_id}"
    bitacora.info(mensaje_termino)

    # Entregar mensaje_termino, nombre_archivo y url_publica
    return mensaje_termino, "", ""
