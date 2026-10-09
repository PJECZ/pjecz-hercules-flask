"""
DGT Digitalizaciones, vistas
"""

import json
from datetime import date, timedelta

from flask import Blueprint, flash, make_response, redirect, render_template, request, url_for
from flask_login import current_user, login_required
from sqlalchemy import Date, cast, func, select
from werkzeug.exceptions import BadRequest, NotFound

from hercules.blueprints.autoridades.models import Autoridad
from hercules.blueprints.bitacoras.models import Bitacora
from hercules.blueprints.dgt_digitalizaciones.models import DgtDigitalizacion
from hercules.blueprints.dgt_digitalizaciones_bitacoras.models import DgtDigitalizacionBitacora
from hercules.blueprints.dgt_rutas.models import DgtRuta
from hercules.blueprints.dgt_tipos.models import DgtTipo
from hercules.blueprints.materias.models import Materia
from hercules.blueprints.modulos.models import Modulo
from hercules.blueprints.permisos.models import Permiso
from hercules.blueprints.usuarios.decorators import permission_required
from hercules.extensions import database
from lib.datatables import get_datatable_parameters, output_datatable_json
from lib.exceptions import (
    MyBucketForbiddenError,
    MyBucketNotFoundError,
    MyFileNotFoundError,
    MyNotValidParamError,
)
from lib.google_cloud_storage import get_blob_name_from_gs_path, get_file_from_gcs
from lib.safe_string import safe_clave, safe_message, safe_string, safe_uuid

MODULO = "DGT DIGITALIZACIONES"
VISTA_PREVIA_PDF_MAX_SIZE_MB = 30 * 1024 * 1024  # 30 MB

dgt_digitalizaciones = Blueprint("dgt_digitalizaciones", __name__, template_folder="templates")


@dgt_digitalizaciones.before_request
@login_required
@permission_required(MODULO, Permiso.VER)
def before_request():
    """Permiso por defecto"""


@dgt_digitalizaciones.route("/dgt_digitalizaciones/datatable_json", methods=["GET", "POST"])
def datatable_json():
    """DataTable JSON para listado de DGT Digitalizaciones"""
    # Tomar parámetros de Datatables
    draw, start, rows_per_page = get_datatable_parameters()
    # Consultar
    consulta = select(
        Autoridad.clave.label("autoridad_clave"),
        DgtDigitalizacion.id,
        DgtDigitalizacion.archivo_actualizado,
        DgtDigitalizacion.archivo_tamano,
        DgtDigitalizacion.expediente,
        DgtDigitalizacion.expediente_anio,
        DgtDigitalizacion.expediente_num,
        DgtDigitalizacion.descripcion,
        DgtDigitalizacion.es_anomalo,
        DgtDigitalizacion.ultimo_evento,
        DgtDigitalizacion.ultimo_evento_creado,
        DgtTipo.clave.label("dgt_tipo_clave"),
    ).join(Autoridad).join(DgtRuta).join(DgtTipo)
    # Primero filtrar por columnas propias
    if "estatus" in request.form:
        consulta = consulta.where(DgtDigitalizacion.estatus == request.form["estatus"])
    else:
        consulta = consulta.where(DgtDigitalizacion.estatus == "A")
    if "expediente" in request.form:
        expediente = safe_string(request.form["expediente"])
        if expediente != "":
            consulta = consulta.where(DgtDigitalizacion.expediente == expediente)
    if "descripcion" in request.form:
        descripcion = safe_string(request.form["descripcion"], save_enie=True)
        if descripcion != "":
            consulta = consulta.where(DgtDigitalizacion.descripcion.contains(descripcion))
    if "dgt_ruta_id" in request.form:
        consulta = consulta.where(DgtDigitalizacion.dgt_ruta_id == request.form["dgt_ruta_id"])
    if "expediente_anio" in request.form:
        try:
            expediente_anio = int(request.form["expediente_anio"])
            consulta = consulta.where(DgtDigitalizacion.expediente_anio == expediente_anio)
        except ValueError:
            pass
    if "archivo_actualizado" in request.form:
        try:
            archivo_actualizado = date.fromisoformat(request.form["archivo_actualizado"])
            consulta = consulta.where(DgtDigitalizacion.archivo_actualizado >= archivo_actualizado)
            consulta = consulta.where(DgtDigitalizacion.archivo_actualizado < archivo_actualizado + timedelta(days=1))
        except ValueError:
            pass
    if "ultimo_evento" in request.form:
        ultimo_evento = safe_string(request.form["ultimo_evento"])
        if ultimo_evento in DgtDigitalizacionBitacora.EVENTOS:
            consulta = consulta.where(DgtDigitalizacion.ultimo_evento == ultimo_evento)
    if request.form.get("es_anomalo") == "1":
        consulta = consulta.where(DgtDigitalizacion.es_anomalo.is_(True))
    # Luego filtrar por columnas de otras tablas
    if "autoridad_clave" in request.form:
        try:
            autoridad_clave = safe_clave(request.form["autoridad_clave"])
            if autoridad_clave != "":
                consulta = consulta.where(Autoridad.clave == autoridad_clave)
        except ValueError:
            pass
    if "materia_id" in request.form:
        try:
            materia_id = int(request.form["materia_id"])
            consulta = consulta.where(Autoridad.materia_id == materia_id)
        except ValueError:
            pass
    # Ordenar y paginar
    total = database.session.execute(select(func.count()).select_from(consulta.subquery())).scalar()
    consulta = (
        consulta.order_by(
            DgtDigitalizacion.expediente_anio,
            DgtDigitalizacion.expediente_num,
            DgtDigitalizacion.descripcion,
        ).offset(start).limit(rows_per_page)
    )
    # Elaborar datos para DataTable
    data = []
    for item in database.session.execute(consulta):
        data.append(
            {
                "autoridad_clave": item.autoridad_clave,
                "detalle": {
                    "expediente": item.expediente,
                    "url": url_for("dgt_digitalizaciones.detail", dgt_digitalizacion_id=item.id),
                },
                "descripcion": item.descripcion,
                "dgt_tipo_clave": item.dgt_tipo_clave,
                "archivo_actualizado": item.archivo_actualizado.strftime("%Y-%m-%d %H:%M") if item.archivo_actualizado else "",
                "archivo_tamano": item.archivo_tamano,
                "ultimo_evento": {
                    "evento": item.ultimo_evento,
                    "creado": item.ultimo_evento_creado.strftime("%Y-%m-%d %H:%M") if item.ultimo_evento_creado else "",
                },
                "es_anomalo": int(item.es_anomalo) if item.es_anomalo is not None else -1,
            }
        )
    # Entregar JSON
    return output_datatable_json(draw, total, data)


@dgt_digitalizaciones.route("/dgt_digitalizaciones")
def list_active():
    """Listado de DGT Digitalizaciones activas"""
    filtros = {"estatus": "A"}
    titulo = "DGT Digitalizaciones"
    # Si viene el año del expediente, filtrar por éste
    if "expediente_anio" in request.args:
        try:
            expediente_anio = int(request.args["expediente_anio"])
            filtros["expediente_anio"] = str(expediente_anio)
            titulo = f"{titulo} del año {expediente_anio}"
        except (KeyError, ValueError):
            pass
    # Si viene la fecha de archivo actualizado, filtrar por ésta
    if "archivo_actualizado" in request.args:
        try:
            archivo_actualizado = date.fromisoformat(request.args["archivo_actualizado"])
            filtros["archivo_actualizado"] = archivo_actualizado.isoformat()
            titulo = f"{titulo} actualizadas el {archivo_actualizado.isoformat()}"
        except ValueError:
            pass
    # Si viene la materia, filtrar por ésta
    if "materia_id" in request.args:
        try:
            materia = Materia.query.get(int(request.args["materia_id"]))
            if materia is not None:
                filtros["materia_id"] = materia.id
                titulo = f"{titulo} en {materia.nombre}"
        except (KeyError, ValueError):
            pass
    # Si viene el último evento, filtrar por éste
    if "ultimo_evento" in request.args:
        ultimo_evento = safe_string(request.args["ultimo_evento"])
        if ultimo_evento in DgtDigitalizacionBitacora.EVENTOS:
            filtros["ultimo_evento"] = ultimo_evento
            titulo = f"{titulo} con último evento {DgtDigitalizacionBitacora.EVENTOS[ultimo_evento].lower()}"
    # Si viene es_anomalo, filtrar por los anómalos
    if request.args.get("es_anomalo") == "1":
        filtros["es_anomalo"] = "1"
        titulo = f"{titulo} anómalas"
    return render_template(
        "dgt_digitalizaciones/list.jinja2",
        filtros=json.dumps(filtros),
        titulo=titulo,
        estatus="A",
        eventos=DgtDigitalizacionBitacora.EVENTOS,
        ultimo_evento=filtros.get("ultimo_evento", ""),
        es_anomalo="es_anomalo" in filtros,
    )


@dgt_digitalizaciones.route("/dgt_digitalizaciones/inactivos")
@permission_required(MODULO, Permiso.ADMINISTRAR)
def list_inactive():
    """Listado de DGT Digitalizaciones inactivas"""
    return render_template(
        "dgt_digitalizaciones/list.jinja2",
        filtros=json.dumps({"estatus": "B"}),
        titulo="DGT Digitalizaciones inactivas",
        estatus="B",
        eventos=DgtDigitalizacionBitacora.EVENTOS,
        ultimo_evento="",
        es_anomalo=False,
    )


@dgt_digitalizaciones.route("/dgt_digitalizaciones/<dgt_digitalizacion_id>")
def detail(dgt_digitalizacion_id):
    """Detalle de una DGT Digitalización"""
    dgt_digitalizacion_id = safe_uuid(dgt_digitalizacion_id)
    if dgt_digitalizacion_id == "":
        flash("ID de DGT Digitalización inválido", "warning")
        return redirect(url_for("dgt_digitalizaciones.list_active"))
    dgt_digitalizacion = DgtDigitalizacion.query.get_or_404(dgt_digitalizacion_id)
    titulo = f"DGT Digitalización {dgt_digitalizacion.autoridad.clave} {dgt_digitalizacion.expediente}"
    if dgt_digitalizacion.descripcion:
        titulo = f"{titulo} {dgt_digitalizacion.descripcion}"
    return render_template(
        "dgt_digitalizaciones/detail.jinja2",
        dgt_digitalizacion=dgt_digitalizacion,
        eventos=DgtDigitalizacionBitacora.EVENTOS,
        titulo=f"{titulo} {dgt_digitalizacion.dgt_ruta.dgt_tipo.clave}",
        vista_previa_pdf_max_size_mb=VISTA_PREVIA_PDF_MAX_SIZE_MB,
    )


@dgt_digitalizaciones.route("/dgt_digitalizaciones/obtener_totales_por_expediente_anio")
def get_totales_por_expediente_anio_json():
    """Obtener los totales de DGT Digitalizaciones por materia y por año en JSON"""

    # Consultar los totales por materia por año
    consulta = (
        database.session.query(
            Materia.id.label("materia_id"),
            Materia.nombre.label("materia"),
            DgtDigitalizacion.expediente_anio.label("anio"),
            func.count(DgtDigitalizacion.id).label("total"),
            func.count(DgtDigitalizacion.entregado).label("entregados_total"),
        )
        .select_from(
            DgtDigitalizacion,
        )
        .join(
            Autoridad,
        )
        .join(
            Materia,
        )
        .where(
            DgtDigitalizacion.estatus == "A",
        )
        .group_by(
            Materia.id,
            Materia.nombre,
            DgtDigitalizacion.expediente_anio,
        )
        .order_by(
            DgtDigitalizacion.expediente_anio,
            Materia.nombre,
        )
        .all()
    )

    # Entregar la lista de totales
    return {
        "success": True,
        "message": "Entrega exitosa del listado de totales por materia",
        "totales": [
            {
                "materia_id": row.materia_id,
                "materia_nombre": row.materia,
                "anio": row.anio,
                "total": row.total,
                "entregado_total": row.entregados_total,
            }
            for row in consulta
        ],
    }


@dgt_digitalizaciones.route("/dgt_digitalizaciones/obtener_totales_por_materia_por_archivo_actualizado")
def get_totales_por_materia_por_archivo_actualizado_json():
    """Obtener los totales de DGT Digitalizaciones por materia y por fecha de archivo actualizado en JSON"""

    # Validar las fechas inicial y final, en formato AAAA-MM-DD
    try:
        fecha_inicial = date.fromisoformat(request.args["fecha_inicial"])
        fecha_final = date.fromisoformat(request.args["fecha_final"])
    except (KeyError, ValueError):
        return {
            "success": False,
            "message": "Las fechas inicial y final son requeridas en formato AAAA-MM-DD",
            "totales": [],
        }
    if fecha_inicial > fecha_final:
        return {
            "success": False,
            "message": "La fecha inicial no puede ser posterior a la fecha final",
            "totales": [],
        }

    # Tomar solo la fecha de archivo_actualizado para agrupar
    fecha = cast(DgtDigitalizacion.archivo_actualizado, Date)

    # Consultar los totales por materia por fecha, incluyendo todo el día de la fecha final
    consulta = (
        database.session.query(
            Materia.id.label("materia_id"),
            Materia.nombre.label("materia"),
            fecha.label("fecha"),
            func.count(DgtDigitalizacion.id).label("total"),
            func.count(DgtDigitalizacion.entregado).label("entregados_total"),
        )
        .select_from(
            DgtDigitalizacion,
        )
        .join(
            Autoridad,
        )
        .join(
            Materia,
        )
        .where(
            DgtDigitalizacion.estatus == "A",
            DgtDigitalizacion.archivo_actualizado >= fecha_inicial,
            DgtDigitalizacion.archivo_actualizado < fecha_final + timedelta(days=1),
        )
        .group_by(
            Materia.id,
            Materia.nombre,
            fecha,
        )
        .order_by(
            fecha,
            Materia.nombre,
        )
        .all()
    )

    # Entregar la lista de totales
    return {
        "success": True,
        "message": "Entrega exitosa del listado de totales por materia y por fecha de archivo actualizado",
        "totales": [
            {
                "materia_id": row.materia_id,
                "materia_nombre": row.materia,
                "fecha": row.fecha.isoformat(),
                "total": row.total,
                "entregados_total": row.entregados_total,
            }
            for row in consulta
        ],
    }


@dgt_digitalizaciones.route("/dgt_digitalizaciones/dashboard_por_expediente_anio")
def dashboard_por_expediente_anio():
    """Tablero de DGT Digitalizaciones por año del expediente"""
    return render_template("dgt_digitalizaciones/dashboard_por_expediente_anio.jinja2")


@dgt_digitalizaciones.route("/dgt_digitalizaciones/dashboard_por_archivo_actualizado")
def dashboard_por_archivo_actualizado():
    """Tablero de DGT Digitalizaciones por archivo actualizado"""
    return render_template("dgt_digitalizaciones/dashboard_por_archivo_actualizado.jinja2")


@dgt_digitalizaciones.route("/dgt_digitalizaciones/obtener_url_para_descargar/<dgt_digitalizacion_id>")
def get_file_public_url_json(dgt_digitalizacion_id):
    """Obtener la URL pública de un archivo"""
    dgt_digitalizacion_id = safe_uuid(dgt_digitalizacion_id)
    if dgt_digitalizacion_id == "":
        return {
            "success": False,
            "message": "ID de DGT Digitalización inválido",
            "url": "",
        }
    dgt_digitalizacion = DgtDigitalizacion.query.get(dgt_digitalizacion_id)
    if dgt_digitalizacion is None:
        return {
            "success": False,
            "message": "No se encontró la DGT Digitalización",
            "url": "",
        }
    bitacora = Bitacora(
        modulo=Modulo.query.filter_by(nombre=MODULO).first(),
        usuario=current_user,
        descripcion=safe_message(f"Se ha descargado {dgt_digitalizacion.autoridad.clave} {dgt_digitalizacion.expediente}"),
        url=url_for("dgt_digitalizaciones.detail", dgt_digitalizacion_id=dgt_digitalizacion.id),
    )
    bitacora.save()
    return {
        "success": True,
        "message": "Entregada la URL pública de un archivo de DGT Digitalización",
        "url": dgt_digitalizacion.archivo_public_url,
    }


@dgt_digitalizaciones.route("/dgt_digitalizaciones/previsualizar_archivo_pdf/<dgt_digitalizacion_id>")
def preview_file_pdf(dgt_digitalizacion_id):
    """Previsualizar un archivo PDF"""
    dgt_digitalizacion_id = safe_uuid(dgt_digitalizacion_id)
    if dgt_digitalizacion_id == "":
        raise BadRequest("ID de DGT Digitalización inválido")
    dgt_digitalizacion = DgtDigitalizacion.query.get(dgt_digitalizacion_id)
    if dgt_digitalizacion is None:
        raise NotFound("DGT Digitalización no encontrada")
    if dgt_digitalizacion.archivo_tamano is not None and dgt_digitalizacion.archivo_tamano > VISTA_PREVIA_PDF_MAX_SIZE_MB:
        raise BadRequest("El archivo es demasiado grande para previsualizarlo.")
    try:
        archivo = get_file_from_gcs(
            bucket_name=dgt_digitalizacion.dgt_ruta.dgt_deposito.clave.lower(),
            blob_name=get_blob_name_from_gs_path(dgt_digitalizacion.archivo_url),
        )
    except MyBucketForbiddenError as error:
        raise BadRequest("No se tiene permiso para acceder al depósito.") from error
    except MyNotValidParamError as error:
        raise BadRequest("Parámetro no válido para acceder al archivo.") from error
    except MyBucketNotFoundError as error:
        raise NotFound("No se encontró el depósito.") from error
    except MyFileNotFoundError as error:
        raise NotFound("No se encontró el archivo.") from error
    bitacora = Bitacora(
        modulo=Modulo.query.filter_by(nombre=MODULO).first(),
        usuario=current_user,
        descripcion=safe_message(f"Se ha previsualizado {dgt_digitalizacion.autoridad.clave} {dgt_digitalizacion.expediente}"),
        url=url_for("dgt_digitalizaciones.detail", dgt_digitalizacion_id=dgt_digitalizacion.id),
    )
    bitacora.save()
    response = make_response(archivo)
    response.headers["Content-Type"] = "application/pdf"
    return response


@dgt_digitalizaciones.route("/dgt_digitalizaciones/descargar_archivo_pdf/<dgt_digitalizacion_id>")
def download_file_pdf(dgt_digitalizacion_id):
    """Previsualizar un archivo PDF"""
    dgt_digitalizacion_id = safe_uuid(dgt_digitalizacion_id)
    if dgt_digitalizacion_id == "":
        raise BadRequest("ID de DGT Digitalización inválido")
    dgt_digitalizacion = DgtDigitalizacion.query.get(dgt_digitalizacion_id)
    if dgt_digitalizacion is None:
        raise NotFound("DGT Digitalización no encontrada")
    if dgt_digitalizacion.archivo_tamano is not None and dgt_digitalizacion.archivo_tamano > VISTA_PREVIA_PDF_MAX_SIZE_MB:
        raise BadRequest("El archivo es demasiado grande para previsualizarlo.")
    try:
        archivo = get_file_from_gcs(
            bucket_name=dgt_digitalizacion.dgt_ruta.dgt_deposito.clave.lower(),
            blob_name=get_blob_name_from_gs_path(dgt_digitalizacion.archivo_url),
        )
    except MyBucketForbiddenError as error:
        raise BadRequest("No se tiene permiso para acceder al depósito.") from error
    except MyNotValidParamError as error:
        raise BadRequest("Parámetro no válido para acceder al archivo.") from error
    except MyBucketNotFoundError as error:
        raise NotFound("No se encontró el depósito.") from error
    except MyFileNotFoundError as error:
        raise NotFound("No se encontró el archivo.") from error
    response = make_response(archivo)
    response.headers["Content-Type"] = "application/pdf"
    response.headers["Content-Disposition"] = f"attachment; filename={dgt_digitalizacion.archivo}"
    return response
