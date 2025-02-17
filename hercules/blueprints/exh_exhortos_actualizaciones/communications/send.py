"""
Communications, Enviar Actualizacion
"""

from hercules.blueprints.exh_exhortos.communications import bitacora


def enviar_actualizacion(exh_exhorto_actualizacion_id: int) -> tuple[str, str, str]:
    """Enviar actualización"""
    bitacora.info("Inicia enviar la actualización al PJ externo")

    # Elaborar mensaje_termino
    mensaje_termino = "Termina enviar la actualización al PJ externo"
    bitacora.info(mensaje_termino)

    # Entregar mensaje_termino, nombre_archivo y url_publica
    return mensaje_termino, "", ""
