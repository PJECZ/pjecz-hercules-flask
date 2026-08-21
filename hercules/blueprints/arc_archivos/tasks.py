"""
Archivo, tareas para ejecutar en el fondo
"""

import locale
import logging
from datetime import date, timedelta

from dotenv import load_dotenv
from sqlalchemy import or_

from hercules.app import create_app
from hercules.blueprints.arc_remesas.models import ArcRemesa
from hercules.blueprints.arc_remesas_bitacoras.models import ArcRemesaBitacora
from hercules.blueprints.arc_solicitudes.models import ArcSolicitud
from hercules.blueprints.arc_solicitudes_bitacoras.models import ArcSolicitudBitacora
from hercules.blueprints.usuarios.models import Usuario
from lib.tasks import set_task_error, set_task_progress

load_dotenv()  # Take environment variables from .env

DIAS_ANTIGUEDAD = 0
DIAS_ANTIGUEDAD_CANCELADAS = 2
USUARIO_DEFECTO = "archivo@pjecz.gob.mx"

bitacora = logging.getLogger(__name__)
bitacora.setLevel(logging.INFO)
formato = logging.Formatter("%(asctime)s:%(levelname)s:%(message)s")
empunadura = logging.FileHandler("logs/arc_archivos.log")
empunadura.setFormatter(formato)
bitacora.addHandler(empunadura)

app = create_app()
app.app_context().push()

locale.setlocale(locale.LC_TIME, "es_MX.utf8")


def pasar_al_historial_solicitudes_completadas():
    """Pasar al historial las solicitudes y remesas con mucha antigüedad habiendo sido procesadas correctamente"""

    # Fecha
    fecha_limite = date.today() - timedelta(days=DIAS_ANTIGUEDAD)

    # Ubicar al usuario responsable para dicha operación
    usuario = Usuario.query.filter_by(email=USUARIO_DEFECTO).filter_by(estatus="A").first()
    if not usuario:
        mensaje_final = f"ERROR: usuario por defecto no localizado '{USUARIO_DEFECTO}'"
        bitacora.error(mensaje_final)
        return mensaje_final

    # Iniciar tarea
    set_task_progress(0, "Inicia pasar al historial solicitudes completadas")

    # Selección de solicitudes con más de tantos días de antigüedad y en estado de recibidos
    solicitudes = (
        ArcSolicitud.query.filter_by(estado="ENTREGADO")
        .filter_by(esta_archivado=False)
        .filter(ArcSolicitud.tiempo_recepcion <= fecha_limite)
        .all()
    )
    contador = 0
    for solicitud in solicitudes:
        solicitud.esta_archivado = True
        solicitud.save()
        contador += 1
        # Añadir acción a la bitácora de Solicitudes
        ArcSolicitudBitacora(
            arc_solicitud=solicitud,
            usuario=usuario,
            accion="PASADA AL HISTORIAL",
            observaciones="Tarea programada",
        ).save()
    if contador <= 0:
        bitacora.info("Solicitudes ENTREGADAS pasadas al historial - No hubo cambios")
    else:
        bitacora.info(
            "Se han pasado al historial %d solicitudes con fechas de recibido mayor a %d días.", contador, DIAS_ANTIGUEDAD
        )

    # Terminar tarea
    set_task_progress(100, "Termina pasar al historial solicitudes completadas")

    return "Terminado satisfactoriamente"


def pasar_al_historial_solicitudes_canceladas():
    """Pasar al historial las solicitudes con determinados días de antigüedad teniendo el estado de canceladas"""

    # Fecha
    fecha_limite = date.today() - timedelta(days=DIAS_ANTIGUEDAD_CANCELADAS)

    # Ubicar al usuario responsable para dicha operación
    usuario = Usuario.query.filter_by(email=USUARIO_DEFECTO).filter_by(estatus="A").first()
    if not usuario:
        mensaje_final = f"ERROR: usuario por defecto no localizado '{USUARIO_DEFECTO}'"
        bitacora.error(mensaje_final)
        return mensaje_final

    # Iniciar tarea
    set_task_progress(0, "Inicia pasar al historial solicitudes canceladas")

    # Selección de solicitudes con más de tantos días de antigüedad y en estado de recibidos
    solicitudes = (
        ArcSolicitud.query.filter_by(estado="CANCELADO")
        .filter_by(esta_archivado=False)
        .filter(ArcSolicitud.modificado <= fecha_limite)
        .all()
    )
    contador = 0
    for solicitud in solicitudes:
        solicitud.esta_archivado = True
        solicitud.save()
        contador += 1
        # Añadir acción a la bitácora de Solicitudes
        ArcSolicitudBitacora(
            arc_solicitud=solicitud,
            usuario=usuario,
            accion="PASADA AL HISTORIAL",
            observaciones="Tarea programada",
        ).save()
    if contador <= 0:
        bitacora.info("Solicitudes CANCELADAS pasadas al historial - No hubo cambios")
    else:
        bitacora.info(
            "Se han pasado al historial %d solicitudes canceladas con más de %d días.", contador, DIAS_ANTIGUEDAD_CANCELADAS
        )

    # Terminar tarea
    set_task_progress(100, "Termina pasar al historial solicitudes canceladas")

    return "Terminado satisfactoriamente"


def pasar_al_historial_remesas_archivadas():
    """Pasar al historial las remesas con determinados días de antigüedad teniendo el estado de archivadas o archivadas con anomalía"""

    # Fecha
    fecha_limite = date.today() - timedelta(days=DIAS_ANTIGUEDAD)

    # Ubicar al usuario responsable para dicha operación
    usuario = Usuario.query.filter_by(email=USUARIO_DEFECTO).filter_by(estatus="A").first()
    if not usuario:
        mensaje_final = f"ERROR: usuario por defecto no localizado '{USUARIO_DEFECTO}'"
        bitacora.error(mensaje_final)
        return mensaje_final

    # Iniciar tarea
    set_task_progress(0, "Inicia pasar al historial remesas archivadas")

    # Selección de solicitudes con más de tantos días de antigüedad y en estado de recibidos
    remesas = (
        ArcRemesa.query.filter(or_(ArcRemesa.estado == "ARCHIVADO", ArcRemesa.estado == "ARCHIVADO CON ANOMALIA"))
        .filter_by(esta_archivado=False)
        .filter(ArcRemesa.modificado <= fecha_limite)
        .all()
    )
    contador = 0
    for remesa in remesas:
        remesa.esta_archivado = True
        remesa.save()
        contador += 1
        # Añadir acción a la bitácora de Solicitudes
        ArcRemesaBitacora(
            arc_remesa=remesa,
            usuario=usuario,
            accion="PASADA AL HISTORIAL",
            observaciones="Tarea programada",
        ).save()
    if contador <= 0:
        bitacora.info("Remesas ARCHIVADAS pasadas al historial - No hubo cambios")
    else:
        bitacora.info(
            "Se han pasado al historial %d remesas con fechas de recibido mayor a %d días.", contador, DIAS_ANTIGUEDAD
        )

    # Terminar tarea
    set_task_progress(100, "Termina pasar al historial remesas archivadas")

    return "Terminado satisfactoriamente"


def pasar_al_historial_remesas_canceladas():
    """Pasar al historial las remesas con determinados días de antigüedad teniendo el estado de canceladas"""

    # Fecha
    fecha_limite = date.today() - timedelta(days=DIAS_ANTIGUEDAD_CANCELADAS)

    # Ubicar al usuario responsable para dicha operación
    usuario = Usuario.query.filter_by(email=USUARIO_DEFECTO).filter_by(estatus="A").first()
    if not usuario:
        mensaje_final = f"ERROR: usuario por defecto no localizado '{USUARIO_DEFECTO}'"
        bitacora.error(mensaje_final)
        return mensaje_final

    # Iniciar tarea
    set_task_progress(0, "Inicia pasar al historial remesas canceladas")

    # Selección de remesas con más de tantos días de antigüedad y en estado de cancelada
    remesas = (
        ArcRemesa.query.filter_by(estado="CANCELADO")
        .filter_by(esta_archivado=False)
        .filter(ArcRemesa.modificado <= fecha_limite)
        .all()
    )
    contador = 0
    for remesa in remesas:
        remesa.esta_archivado = True
        remesa.save()
        contador += 1
        # Añadir acción a la bitácora de remesas
        ArcRemesaBitacora(
            arc_remesa=remesa,
            usuario=usuario,
            accion="PASADA AL HISTORIAL",
            observaciones="Tarea programada",
        ).save()
    if contador <= 0:
        bitacora.info("Remesas CANCELADAS pasadas al historial - No hubo cambios")
    else:
        bitacora.info(
            "Se han pasado al historial %d remesas canceladas con más de %d días.", contador, DIAS_ANTIGUEDAD_CANCELADAS
        )

    # Terminar tarea
    set_task_progress(100, "Termina pasar al historial remesas canceladas")

    return "Terminado satisfactoriamente"


def pasar_al_historial_remesas_rechazadas():
    """Pasar al historial las remesas con determinados días de antigüedad teniendo el estado de rechazadas"""

    # Fecha
    fecha_limite = date.today() - timedelta(days=DIAS_ANTIGUEDAD_CANCELADAS)

    # Ubicar al usuario responsable para dicha operación
    usuario = Usuario.query.filter_by(email=USUARIO_DEFECTO).filter_by(estatus="A").first()
    if not usuario:
        mensaje_final = f"ERROR: usuario por defecto no localizado '{USUARIO_DEFECTO}'"
        bitacora.error(mensaje_final)
        return mensaje_final

    # Iniciar tarea
    set_task_progress(0, "Inicia pasar al historial remesas rechazadas")

    # Selección de remesas con más de tantos días de antigüedad y en estado de cancelada
    remesas = (
        ArcRemesa.query.filter_by(estado="RECHAZADO")
        .filter_by(esta_archivado=False)
        .filter(ArcRemesa.modificado <= fecha_limite)
        .all()
    )
    contador = 0
    for remesa in remesas:
        remesa.esta_archivado = True
        remesa.save()
        contador += 1
        # Añadir acción a la bitácora de remesas
        ArcRemesaBitacora(
            arc_remesa=remesa,
            usuario=usuario,
            accion="PASADA AL HISTORIAL",
            observaciones="Tarea programada",
        ).save()
    if contador <= 0:
        bitacora.info("Remesas RECHAZADO pasadas al historial - No hubo cambios")
    else:
        bitacora.info(
            "Se han pasado al historial %d remesas rechazadas con más de %d días.", contador, DIAS_ANTIGUEDAD_CANCELADAS
        )

    # Terminar tarea
    set_task_progress(100, "Termina pasar al historial remesas rechazadas")

    return "Terminado satisfactoriamente"
