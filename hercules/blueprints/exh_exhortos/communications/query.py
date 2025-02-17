"""
Communications, Consultar Exhorto
"""

from hercules.blueprints.exh_exhortos.communications import bitacora


def consultar_exhorto(exh_exhorto_id: int) -> tuple[str, str, str]:
    """Consultar exhortos"""
    bitacora.info("Inicia consultar exhorto al PJ externo.")

    # Juntar todos los items del listado en un texto para que sea el mensaje_termino
    mensaje_termino = f"Se consultó el exhorto con ID {exh_exhorto_id} al PJ externo."
    bitacora.info(mensaje_termino)

    # Entregar mensaje_termino, nombre_archivo y url_publica
    return mensaje_termino, "", ""
