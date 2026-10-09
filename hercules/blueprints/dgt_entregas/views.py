"""
DGT Entregas, vistas
"""

import json
from datetime import date, timedelta

from flask import Blueprint, flash, make_response, redirect, render_template, request, url_for
from flask_login import current_user, login_required
from sqlalchemy import Date, cast, func, select
from werkzeug.exceptions import BadRequest, NotFound

from hercules.blueprints.autoridades.models import Autoridad
from hercules.blueprints.bitacoras.models import Bitacora
from hercules.blueprints.dgt_entregas.models import DgtEntrega
from hercules.blueprints.dgt_entregas_bitacoras.models import DgtEntregaBitacora
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

MODULO = "DGT ENTREGAS"
VISTA_PREVIA_PDF_MAX_SIZE_MB = 30 * 1024 * 1024  # 30 MB

dgt_entregas = Blueprint("dgt_entregas", __name__, template_folder="templates")


@dgt_entregas.before_request
@login_required
@permission_required(MODULO, Permiso.VER)
def before_request():
    """Permiso por defecto"""


@dgt_entregas.route("/dgt_entregas/datatable_json", methods=["GET", "POST"])
def datatable_json():
    """DataTable JSON para listado de DGT Entregas"""
    # Tomar parámetros de Datatables
    draw, start, rows_per_page = get_datatable_parameters()
    # Consultar
    consulta = select(
        Autoridad.clave.label("autoridad_clave"),
        DgtEntrega.id,
        DgtEntrega.archivo_nombre,
        DgtEntrega.archivo_actualizado,
        DgtEntrega.archivo_tamano,
        DgtEntrega.archivo_uuid,
        DgtEntrega.es_anomalo,
        DgtEntrega.expediente,
        DgtEntrega.descripcion,
        DgtEntrega.ultimo_evento,
        DgtEntrega.ultimo_evento_creado,
        DgtTipo.clave.label("dgt_tipo_clave"),
    ).join(Autoridad).join(DgtRuta).join(DgtTipo)
    # Primero filtrar por columnas propias
    if "estatus" in request.form:
        consulta = consulta.where(DgtEntrega.estatus == request.form["estatus"])
    else:
        consulta = consulta.where(DgtEntrega.estatus == "A")
    if "expediente" in request.form:
        expediente = safe_string(request.form["expediente"])
        if expediente != "":
            consulta = consulta.where(DgtEntrega.expediente == expediente)
    if "descripcion" in request.form:
        descripcion = safe_string(request.form["descripcion"], save_enie=True)
        if descripcion != "":
            consulta = consulta.where(DgtEntrega.descripcion.contains(descripcion))
    if "dgt_ruta_id" in request.form:
        consulta = consulta.where(DgtEntrega.dgt_ruta_id == request.form["dgt_ruta_id"])
    if "expediente_anio" in request.form:
        try:
            expediente_anio = int(request.form["expediente_anio"])
            consulta = consulta.where(DgtEntrega.expediente_anio == expediente_anio)
        except ValueError:
            pass
    if "archivo_actualizado" in request.form:
        try:
            archivo_actualizado = date.fromisoformat(request.form["archivo_actualizado"])
            consulta = consulta.where(DgtEntrega.archivo_actualizado >= archivo_actualizado)
            consulta = consulta.where(DgtEntrega.archivo_actualizado < archivo_actualizado + timedelta(days=1))
        except ValueError:
            pass
    if "ultimo_evento" in request.form:
        ultimo_evento = safe_string(request.form["ultimo_evento"])
        if ultimo_evento in DgtEntregaBitacora.EVENTOS:
            consulta = consulta.where(DgtEntrega.ultimo_evento == ultimo_evento)
    if request.form.get("archivo_uuid_nulo") == "1":
        consulta = consulta.where(DgtEntrega.archivo_uuid.is_(None))
    if request.form.get("es_anomalo") == "1":
        consulta = consulta.where(DgtEntrega.es_anomalo.is_(True))
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
        consulta.order_by(DgtEntrega.archivo_actualizado.desc())
        .offset(start)
        .limit(rows_per_page)
    )
    # Elaborar datos para DataTable
    data = []
    for item in database.session.execute(consulta):
        data.append(
            {
                "autoridad_clave": item.autoridad_clave,
                "detalle": {
                    "archivo_nombre": item.archivo_nombre,
                    "url": url_for("dgt_entregas.detail", dgt_entrega_id=item.id),
                },
                "expediente": item.expediente,
                "descripcion": item.descripcion,
                "dgt_tipo_clave": item.dgt_tipo_clave,
                "archivo_actualizado": item.archivo_actualizado.strftime("%Y-%m-%d %H:%M"),
                "archivo_tamano": item.archivo_tamano,
                "ultimo_evento": {
                    "evento": item.ultimo_evento,
                    "creado": item.ultimo_evento_creado.strftime("%Y-%m-%d %H:%M") if item.ultimo_evento_creado else "",
                },
                "archivo_uuid": item.archivo_uuid,
                "es_anomalo": int(item.es_anomalo) if item.es_anomalo is not None else -1,
            }
        )
    # Entregar JSON
    return output_datatable_json(draw, total, data)


@dgt_entregas.route("/dgt_entregas")
def list_active():
    """Listado de DGT Entregas activas"""
    filtros = {"estatus": "A"}
    titulo = "DGT Entregas"
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
        if ultimo_evento in DgtEntregaBitacora.EVENTOS:
            filtros["ultimo_evento"] = ultimo_evento
            titulo = f"{titulo} con último evento {DgtEntregaBitacora.EVENTOS[ultimo_evento].lower()}"
    # Si viene archivo_uuid_nulo, filtrar por los que no tienen UUID
    if request.args.get("archivo_uuid_nulo") == "1":
        filtros["archivo_uuid_nulo"] = "1"
        titulo = f"{titulo} sin UUID"
    # Si viene es_anomalo, filtrar por los anómalos
    if request.args.get("es_anomalo") == "1":
        filtros["es_anomalo"] = "1"
        titulo = f"{titulo} anómalas"
    return render_template(
        "dgt_entregas/list.jinja2",
        filtros=json.dumps(filtros),
        titulo=titulo,
        estatus="A",
        eventos=DgtEntregaBitacora.EVENTOS,
        ultimo_evento=filtros.get("ultimo_evento", ""),
        archivo_uuid_nulo="archivo_uuid_nulo" in filtros,
        es_anomalo="es_anomalo" in filtros,
    )


@dgt_entregas.route("/dgt_entregas/inactivos")
@permission_required(MODULO, Permiso.ADMINISTRAR)
def list_inactive():
    """Listado de DGT Entregas inactivas"""
    return render_template(
        "dgt_entregas/list.jinja2",
        filtros=json.dumps({"estatus": "B"}),
        titulo="DGT Entregas inactivas",
        estatus="B",
        eventos=DgtEntregaBitacora.EVENTOS,
        ultimo_evento="",
        archivo_uuid_nulo=False,
        es_anomalo=False,
    )


@dgt_entregas.route("/dgt_entregas/<dgt_entrega_id>")
def detail(dgt_entrega_id):
    """Detalle de una DGT Entrega"""
    dgt_entrega_id = safe_uuid(dgt_entrega_id)
    if dgt_entrega_id == "":
        flash("ID de DGT Entrega inválido", "warning")
        return redirect(url_for("dgt_entregas.list_active"))
    dgt_entrega = DgtEntrega.query.get_or_404(dgt_entrega_id)
    titulo = f"DGT Entrega {dgt_entrega.autoridad.clave}"
    if dgt_entrega.expediente:
        titulo = f"{titulo} {dgt_entrega.expediente}"
    if dgt_entrega.descripcion:
        titulo = f"{titulo} {dgt_entrega.descripcion}"
    return render_template(
        "dgt_entregas/detail.jinja2",
        dgt_entrega=dgt_entrega,
        titulo=f"{titulo} {dgt_entrega.dgt_ruta.dgt_tipo.clave}",
        vista_previa_pdf_max_size_mb=VISTA_PREVIA_PDF_MAX_SIZE_MB,
    )


@dgt_entregas.route("/dgt_entregas/obtener_totales_por_expediente_anio")
def get_totales_por_expediente_anio_json():
    """Obtener los totales de DGT Entregas por materia y por año en JSON"""

    # Consultar los totales por materia por año
    consulta = (
        database.session.query(
            Materia.id.label("materia_id"),
            Materia.nombre.label("materia"),
            DgtEntrega.expediente_anio.label("anio"),
            func.count(DgtEntrega.id).label("total"),
        )
        .select_from(
            DgtEntrega,
        )
        .join(
            Autoridad,
        )
        .join(
            Materia,
        )
        .where(
            DgtEntrega.estatus == "A",
        )
        .group_by(
            Materia.id,
            Materia.nombre,
            DgtEntrega.expediente_anio,
        )
        .order_by(
            DgtEntrega.expediente_anio,
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
            }
            for row in consulta
        ],
    }


@dgt_entregas.route("/dgt_entregas/obtener_totales_por_materia_por_archivo_actualizado")
def get_totales_por_materia_por_archivo_actualizado_json():
    """Obtener los totales de DGT Entregas por materia y por fecha de archivo actualizado en JSON"""

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
    fecha = cast(DgtEntrega.archivo_actualizado, Date)

    # Consultar los totales por materia por fecha, incluyendo todo el día de la fecha final
    consulta = (
        database.session.query(
            Materia.id.label("materia_id"),
            Materia.nombre.label("materia"),
            fecha.label("fecha"),
            func.count(DgtEntrega.id).label("total"),
        )
        .select_from(
            DgtEntrega,
        )
        .join(
            Autoridad,
        )
        .join(
            Materia,
        )
        .where(
            DgtEntrega.estatus == "A",
            DgtEntrega.archivo_actualizado >= fecha_inicial,
            DgtEntrega.archivo_actualizado < fecha_final + timedelta(days=1),
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
            }
            for row in consulta
        ],
    }


@dgt_entregas.route("/dgt_entregas/dashboard_por_expediente_anio")
def dashboard_por_expediente_anio():
    """Tablero de DGT Entregas por año del expediente"""
    return render_template("dgt_entregas/dashboard_por_expediente_anio.jinja2")


@dgt_entregas.route("/dgt_entregas/dashboard_por_archivo_actualizado")
def dashboard_por_archivo_actualizado():
    """Tablero de DGT Entregas por archivo actualizado"""
    return render_template("dgt_entregas/dashboard_por_archivo_actualizado.jinja2")


@dgt_entregas.route("/dgt_entregas/obtener_url_para_descargar/<dgt_entrega_id>")
def get_file_public_url_json(dgt_entrega_id):
    """Obtener la URL pública de un archivo"""
    dgt_entrega_id = safe_uuid(dgt_entrega_id)
    if dgt_entrega_id == "":
        return {
            "success": False,
            "message": "ID de DGT Entrega inválido",
            "url": "",
        }
    dgt_entrega = DgtEntrega.query.get(dgt_entrega_id)
    if dgt_entrega is None:
        return {
            "success": False,
            "message": "No se encontró la DGT Entrega",
            "url": "",
        }
    bitacora = Bitacora(
        modulo=Modulo.query.filter_by(nombre=MODULO).first(),
        usuario=current_user,
        descripcion=safe_message(f"Se ha descargado {dgt_entrega.autoridad.clave} {dgt_entrega.expediente}"),
        url=url_for("dgt_entregas.detail", dgt_entrega_id=dgt_entrega.id),
    )
    bitacora.save()
    return {
        "success": True,
        "message": "Entregada la URL pública de un archivo de DGT Entrega",
        "url": dgt_entrega.archivo_public_url,
    }


@dgt_entregas.route("/dgt_entregas/previsualizar_archivo_pdf/<dgt_entrega_id>")
def preview_file_pdf(dgt_entrega_id):
    """Previsualizar un archivo PDF"""
    dgt_entrega_id = safe_uuid(dgt_entrega_id)
    if dgt_entrega_id == "":
        raise BadRequest("ID de DGT Entrega inválido")
    dgt_entrega = DgtEntrega.query.get(dgt_entrega_id)
    if dgt_entrega is None:
        raise NotFound("DGT Entrega no encontrada")
    if dgt_entrega.archivo_tamano is not None and dgt_entrega.archivo_tamano > VISTA_PREVIA_PDF_MAX_SIZE_MB:
        raise BadRequest("El archivo es demasiado grande para previsualizarlo.")
    try:
        archivo = get_file_from_gcs(
            bucket_name=dgt_entrega.dgt_ruta.dgt_deposito.clave.lower(),
            blob_name=get_blob_name_from_gs_path(dgt_entrega.archivo_url),
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
        descripcion=safe_message(f"Se ha previsualizado {dgt_entrega.autoridad.clave} {dgt_entrega.expediente}"),
        url=url_for("dgt_entregas.detail", dgt_entrega_id=dgt_entrega.id),
    )
    bitacora.save()
    response = make_response(archivo)
    response.headers["Content-Type"] = "application/pdf"
    return response


@dgt_entregas.route("/dgt_entregas/descargar_archivo_pdf/<dgt_entrega_id>")
def download_file_pdf(dgt_entrega_id):
    """Previsualizar un archivo PDF"""
    dgt_entrega_id = safe_uuid(dgt_entrega_id)
    if dgt_entrega_id == "":
        raise BadRequest("ID de DGT Entrega inválido")
    dgt_entrega = DgtEntrega.query.get(dgt_entrega_id)
    if dgt_entrega is None:
        raise NotFound("DGT Entrega no encontrada")
    if dgt_entrega.archivo_tamano is not None and dgt_entrega.archivo_tamano > VISTA_PREVIA_PDF_MAX_SIZE_MB:
        raise BadRequest("El archivo es demasiado grande para previsualizarlo.")
    try:
        archivo = get_file_from_gcs(
            bucket_name=dgt_entrega.dgt_ruta.dgt_deposito.clave.lower(),
            blob_name=get_blob_name_from_gs_path(dgt_entrega.archivo_url),
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
    response.headers["Content-Disposition"] = f"attachment; filename={dgt_entrega.archivo}"
    return response
