"""
Tareas en el fondo, 04 consultar exhorto
"""

import logging

bitacora = logging.getLogger(__name__)
bitacora.setLevel(logging.INFO)
formato = logging.Formatter("%(asctime)s:%(levelname)s:%(message)s")
empunadura = logging.FileHandler("logs/exh_exhortos.log")
empunadura.setFormatter(formato)
bitacora.addHandler(empunadura)


def consultar(exh_exhorto_id: int) -> tuple[str, str, str]:
    """Consultar exhortos"""
    bitacora.info("Inicia consultar")

    # Elaborar mensaje_termino
    mensaje_termino = "Termina consultar"
    bitacora.info(mensaje_termino)

    # Entregar mensaje_termino, nombre_archivo y url_publica
    return mensaje_termino, "", ""
