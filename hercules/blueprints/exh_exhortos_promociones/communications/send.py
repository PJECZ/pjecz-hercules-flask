"""
Communications, Enviar Promocion
"""

import requests

from hercules.app import create_app
from hercules.blueprints.estados.models import Estado
from hercules.blueprints.exh_exhortos.communications import bitacora
from hercules.blueprints.exh_exhortos_promociones.models import ExhExhortoPromocion
from hercules.blueprints.exh_externos.models import ExhExterno
from hercules.blueprints.municipios.models import Municipio
from hercules.extensions import database
from lib.exceptions import (
    MyAnyError,
    MyBucketNotFoundError,
    MyConnectionError,
    MyFileNotFoundError,
    MyNotExistsError,
    MyNotValidParamError,
)

app = create_app()
app.app_context().push()
database.app = app

TIMEOUT = 60  # segundos


def enviar_promocion(exh_exhorto_promocion_id: int) -> tuple[str, str, str]:
    """Enviar promoción"""
    bitacora.info("Inicia enviar promoción")

    # Consultar la promoción
    exh_exhorto_promocion = ExhExhortoPromocion.query.get(exh_exhorto_promocion_id)

    # Validar que exista la promoción
    if exh_exhorto_promocion is None:
        mensaje_advertencia = f"No existe la promoción con ID {exh_exhorto_promocion_id}"
        bitacora.error(mensaje_advertencia)
        raise MyNotExistsError(mensaje_advertencia)

    # Validar que su estado sea POR ENVIAR
    if exh_exhorto_promocion.estado != "PENDIENTE":
        mensaje_advertencia = f"La promoción con ID {exh_exhorto_promocion_id} no tiene el estado PENDIENTE"
        bitacora.error(mensaje_advertencia)
        raise MyNotExistsError(mensaje_advertencia)

    # Consultar el Estado de destino a partir del ID del Municipio en municipio_destino_id
    municipio = Municipio.query.get(exh_exhorto_promocion.exh_exhorto.municipio_destino_id)
    if municipio is None:
        mensaje_advertencia = f"No existe el municipio con ID {exh_exhorto_promocion.exh_exhorto.municipio_destino_id}"
        bitacora.error(mensaje_advertencia)
        raise MyNotExistsError(mensaje_advertencia)
    estado = Estado.query.get(municipio.estado_id)
    if estado is None:
        mensaje_advertencia = f"No existe el estado con ID {municipio.estado_id}"
        bitacora.error(mensaje_advertencia)
        raise MyNotExistsError(mensaje_advertencia)

    # Consultar el ExhExterno con el ID del Estado, tomar el primero porque solo debe haber uno
    exh_externo = ExhExterno.query.filter_by(estado_id=estado.id).first()
    if exh_externo is None:
        mensaje_advertencia = f"No hay datos en exh_externos del estado {estado.nombre}"
        bitacora.error(mensaje_advertencia)
        raise MyNotExistsError(mensaje_advertencia)

    # Si exh_externo no tiene API-key
    if exh_externo.api_key is None or exh_externo.api_key == "":
        mensaje_advertencia = f"No tiene API-key en exh_externos el estado {estado.nombre}"
        bitacora.error(mensaje_advertencia)
        raise MyNotExistsError(mensaje_advertencia)

    # Si exh_externo no tiene endpoint para enviar promociones
    if exh_externo.endpoint_recibir_promocion is None or exh_externo.endpoint_recibir_promocion == "":
        mensaje_advertencia = f"No tiene endpoint para enviar promociones el estado {estado.nombre}"
        bitacora.error(mensaje_advertencia)
        raise MyNotExistsError(mensaje_advertencia)

    # Si exh_externo no tiene endpoint para enviar archivos
    if exh_externo.endpoint_recibir_promocion_archivo is None or exh_externo.endpoint_recibir_promocion_archivo == "":
        mensaje_advertencia = f"No tiene endpoint para enviar archivos de promociones el estado {estado.nombre}"
        bitacora.error(mensaje_advertencia)
        raise MyNotExistsError(mensaje_advertencia)

    # Bucle para juntar los promoventes
    promoventes = []
    for promovente in exh_exhorto_promocion.exh_exhortos_promociones_promoventes:
        promoventes.append(
            {
                "nombre": str(promovente.nombre),
                "apellidoPaterno": str(promovente.apellido_paterno),
                "apellidoMaterno": str(promovente.apellido_materno),
                "genero": str(promovente.genero),
                "esPersonaMoral": bool(promovente.es_persona_moral),
                "tipoParte": int(promovente.tipo_parte),
                "tipoParteNombre": str(promovente.tipo_parte_nombre),
            }
        )

    # Bucle para juntar los archivos
    archivos = []
    for archivo in exh_exhorto_promocion.exh_exhortos_promociones_archivos:
        archivos.append(
            {
                "nombreArchivo": str(archivo.nombre_archivo),
                "hashSha1": str(archivo.hash_sha1),
                "hashSha256": str(archivo.hash_sha256),
                "tipoDocumento": int(archivo.tipo_documento),
            }
        )

    # Definir los datos de la promoción a enviar
    datos_promocion = {
        "folioSeguimiento": exh_exhorto_promocion.exh_exhorto.folio_seguimiento,
        "folioOrigenPromocion": "PENDIENTE-FOLIO-ORIGEN-PROMOCION",
        "promoventes": promoventes,
        "fojas": int(exh_exhorto_promocion.fojas),
        "fechaOrigen": exh_exhorto_promocion.fecha_origen.strftime("%Y-%m-%d %H:%M:%S"),
        "observaciones": str(exh_exhorto_promocion.observaciones),
        "archivos": archivos,
    }

    # Informar a la bitácora que se va a enviar la promoción
    mensaje = "Pasan las validaciones y comienza el envío de la promoción."
    bitacora.info(mensaje)

    # Enviar la promoción

    # Terminar si hubo mensaje_advertencia

    # Terminar si el contenido de la respuesta no es valido

    # Terminar si success es FALSO

    # Informar a la bitácora que terminó el envío la promoción
    mensaje = "Termina el envío la promoción."
    bitacora.info(mensaje)

    # Informar a la bitácora que se van a enviar los archivos de la promoción
    mensaje = "Comienza el envío de los archivos de la promoción."
    bitacora.info(mensaje)

    # Mandar los archivos del exhorto con multipart/form-data (ETAPA 3)

    # Informar a la bitácora que terminó el envío los archivos
    mensaje = "Termina el envío de los archivos de la promoción."
    bitacora.info(mensaje)

    # Inicializar mensaje_advertencia para acumular fallos si los hubiera
    mensaje_advertencia = ""

    # Validar que el ULTIMO acuse tenga en el data

    # Cambiar el estado a RECHAZADO y terminar si hubo mensaje_advertencia

    # Actualizar el estado a ENVIADO

    # Elaborar mensaje final
    mensaje_termino = f"Termina enviar la promoción con ID {exh_exhorto_promocion_id} al PJ externo."
    bitacora.info(mensaje_termino)

    # Entregar mensaje_termino, nombre_archivo y url_publica
    return mensaje_termino, "", ""
