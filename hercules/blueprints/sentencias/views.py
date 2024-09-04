"""
Sentencias, vistas
"""

import json
import re
from urllib.parse import quote

from flask import Blueprint, current_app, flash, redirect, render_template, request, url_for
from flask_login import current_user, login_required
from pytz import timezone

from hercules.blueprints.autoridades.models import Autoridad
from hercules.blueprints.bitacoras.models import Bitacora
from hercules.blueprints.distritos.models import Distrito
from hercules.blueprints.materias.models import Materia
from hercules.blueprints.materias_tipos_juicios.models import MateriaTipoJuicio
from hercules.blueprints.modulos.models import Modulo
from hercules.blueprints.permisos.models import Permiso
from hercules.blueprints.sentencias.models import Sentencia
from hercules.blueprints.usuarios.decorators import permission_required
from lib.datatables import get_datatable_parameters, output_datatable_json
from lib.exceptions import MyAnyError
from lib.google_cloud_storage import get_blob_name_from_url, get_file_from_gcs, get_media_type_from_filename
from lib.safe_string import safe_clave, safe_expediente, safe_sentencia, safe_string

HUSO_HORARIO = "America/Mexico_City"
MODULO = "SENTENCIAS"
LIMITE_DIAS = 365  # Un anio
LIMITE_ADMINISTRADORES_DIAS = 7300  # Administradores pueden manipular veinte anios

# Roles que deben estar en la base de datos
ROL_REPORTES_TODOS = ["ADMINISTRADOR", "ESTADISTICA", "VISITADURIA JUDICIAL"]

sentencias = Blueprint("sentencias", __name__, template_folder="templates")


@sentencias.before_request
@login_required
@permission_required(MODULO, Permiso.VER)
def before_request():
    """Permiso por defecto"""


@sentencias.route("/sentencias/datatable_json", methods=["GET", "POST"])
def datatable_json():
    """DataTable JSON para listado de Sentencias"""
    # Tomar parámetros de Datatables
    draw, start, rows_per_page = get_datatable_parameters()
    # Consultar
    consulta = Sentencia.query
    # Primero filtrar por columnas propias
    if "estatus" in request.form:
        consulta = consulta.filter_by(estatus=request.form["estatus"])
    else:
        consulta = consulta.filter_by(estatus="A")
    if "autoridad_id" in request.form:
        autoridad = Autoridad.query.get(request.form["autoridad_id"])
        if autoridad:
            consulta = consulta.filter(Sentencia.autoridad_id == autoridad.id)
    if "autoridad_clave" in request.form:
        try:
            autoridad_clave = safe_clave(request.form["autoridad_clave"])
            if autoridad_clave != "":
                consulta = consulta.join(Autoridad).filter(Autoridad.clave.contains(autoridad_clave))
                print(consulta)
        except ValueError:
            pass
    if "sentencia" in request.form:
        try:
            sentencia = safe_sentencia(request.form["sentencia"])
            consulta = consulta.filter(Sentencia.sentencia == sentencia)
        except (IndexError, ValueError):
            pass
    if "expediente" in request.form:
        try:
            expediente = safe_expediente(request.form["expediente"])
            consulta = consulta.filter_by(expediente=expediente)
        except (IndexError, ValueError):
            pass
    # Filtrar por fechas, si vienen invertidas se corrigen
    fecha_desde = None
    fecha_hasta = None
    if "fecha_desde" in request.form and re.match(r"\d{4}-\d{2}-\d{2}", request.form["fecha_desde"]):
        fecha_desde = request.form["fecha_desde"]
    if "fecha_hasta" in request.form and re.match(r"\d{4}-\d{2}-\d{2}", request.form["fecha_hasta"]):
        fecha_hasta = request.form["fecha_hasta"]
    if fecha_desde and fecha_hasta and fecha_desde > fecha_hasta:
        fecha_desde, fecha_hasta = fecha_hasta, fecha_desde
    if fecha_desde:
        consulta = consulta.filter(Sentencia.fecha >= fecha_desde)
    if fecha_hasta:
        consulta = consulta.filter(Sentencia.fecha <= fecha_hasta)
    # Filtrar por tipo de juicio
    if "materia_tipo_juicio_id" in request.form:
        materia_tipo_juicio = MateriaTipoJuicio.query.get(request.form["materia_tipo_juicio_id"])
        if materia_tipo_juicio:
            consulta = consulta.filter(Sentencia.materia_tipo_juicio == materia_tipo_juicio)
    # Ordenar y paginar
    registros = consulta.order_by(Sentencia.fecha.desc()).offset(start).limit(rows_per_page).all()
    total = consulta.count()
    # Elaborar datos para DataTable
    data = []
    for resultado in registros:
        data.append(
            {
                "detalle": {
                    "sentencia": resultado.sentencia,
                    "url": url_for("sentencias.detail", sentencia_id=resultado.id),
                },
                "fecha": resultado.fecha.strftime("%Y-%m-%d"),
                "autoridad": resultado.autoridad.clave,
                "expediente": resultado.expediente,
                "materia_nombre": resultado.materia_tipo_juicio.materia.nombre,
                "materia_tipo_juicio_descripcion": resultado.materia_tipo_juicio.descripcion,
                "es_perspectiva_genero": "Sí" if resultado.es_perspectiva_genero else "",
                "archivo": {
                    "descargar_url": resultado.descargar_url,
                },
            }
        )
    # Entregar JSON
    return output_datatable_json(draw, total, data)


@sentencias.route("/sentencias/datatable_json_admin", methods=["GET", "POST"])
def datatable_json_admin():
    """DataTable JSON para listado de Sentencias admin"""
    # Tomar parámetros de Datatables
    draw, start, rows_per_page = get_datatable_parameters()
    # Consultar
    consulta = Sentencia.query
    # Primero filtrar por columnas propias
    if "estatus" in request.form:
        consulta = consulta.filter_by(estatus=request.form["estatus"])
    else:
        consulta = consulta.filter_by(estatus="A")
    if "autoridad_id" in request.form:
        autoridad = Autoridad.query.get(request.form["autoridad_id"])
        if autoridad:
            consulta = consulta.filter(Sentencia.autoridad_id == autoridad.id)
    if "sentencia" in request.form:
        try:
            sentencia = safe_sentencia(request.form["sentencia"])
            consulta = consulta.filter(Sentencia.sentencia == sentencia)
        except (IndexError, ValueError):
            pass
    if "expediente" in request.form:
        try:
            expediente = safe_expediente(request.form["expediente"])
            consulta = consulta.filter(Sentencia.expediente == expediente)
        except (IndexError, ValueError):
            pass
    # Filtrar por fechas, si vienen invertidas se corrigen
    fecha_desde = None
    fecha_hasta = None
    if "fecha_desde" in request.form and re.match(r"\d{4}-\d{2}-\d{2}", request.form["fecha_desde"]):
        fecha_desde = request.form["fecha_desde"]
    if "fecha_hasta" in request.form and re.match(r"\d{4}-\d{2}-\d{2}", request.form["fecha_hasta"]):
        fecha_hasta = request.form["fecha_hasta"]
    if fecha_desde and fecha_hasta and fecha_desde > fecha_hasta:
        fecha_desde, fecha_hasta = fecha_hasta, fecha_desde
    if fecha_desde:
        consulta = consulta.filter(Sentencia.fecha >= fecha_desde)
    if fecha_hasta:
        consulta = consulta.filter(Sentencia.fecha <= fecha_hasta)
    # Luego filtrar por columnas de otras tablas
    if "materia_id" in request.form:
        materia = Materia.query.get(request.form["materia_id"])
        if materia:
            consulta = consulta.join(MateriaTipoJuicio).filter(MateriaTipoJuicio.materia_id == materia.id)
    if "materia_tipo_juicio_id" in request.form:
        materia_tipo_juicio = MateriaTipoJuicio.query.get(request.form["materia_tipo_juicio_id"])
        if materia_tipo_juicio:
            consulta = consulta.filter(Sentencia.materia_tipo_juicio_id == materia_tipo_juicio.id)
    # Ordenar y paginar
    registros = consulta.order_by(Sentencia.id).offset(start).limit(rows_per_page).all()
    total = consulta.count()
    # Zona horaria local
    local_tz = timezone(HUSO_HORARIO)
    # Elaborar datos para DataTable
    data = []
    for resultado in registros:
        creado_local = resultado.creado.astimezone(local_tz)  # La columna creado esta en UTC, convertir a local
        data.append(
            {
                "detalle": {
                    "id": resultado.id,
                    "url": url_for("sentencias.detail", sentencia_id=resultado.id),
                },
                "creado": creado_local.strftime("%Y-%m-%d %H:%M:%S"),
                "autoridad": resultado.autoridad.clave,
                "fecha": resultado.fecha.strftime("%Y-%m-%d"),
                "sentencia": resultado.sentencia,
                "expediente": resultado.expediente,
                "materia_nombre": resultado.materia_tipo_juicio.materia.nombre,
                "materia_tipo_juicio_descripcion": resultado.materia_tipo_juicio.descripcion,
                "es_perspectiva_genero": "Sí" if resultado.es_perspectiva_genero else "",
                "archivo": {
                    "descargar_url": url_for("sentencias.download", url=quote(resultado.url)),
                },
            }
        )
    # Entregar JSON
    return output_datatable_json(draw, total, data)


@sentencias.route("/sentencias")
def list_active():
    """Listado de Sentencias activos"""
    # Si es administrador ve todo
    if current_user.can_admin("SENTENCIAS"):
        return render_template(
            "sentencias/list_admin.jinja2",
            autoridad=None,
            filtros=json.dumps({"estatus": "A"}),
            titulo="Todas las V.P. de Sentencias",
            estatus="A",
            form=None,
        )
    # Si es jurisdiccional ve lo de su autoridad
    if current_user.autoridad.es_jurisdiccional:
        autoridad = current_user.autoridad
        # form = SentenciaReportForm()
        # form.autoridad_id.data = autoridad.id  # Oculto la autoridad del usuario
        # form.fecha_desde.data = datetime.date.today().replace(day=1)  # Por defecto fecha_desde es el primer dia del mes actual
        # form.fecha_hasta.data = datetime.date.today()  # Por defecto fecha_hasta es hoy
        return render_template(
            "sentencias/list.jinja2",
            autoridad=autoridad,
            filtros=json.dumps({"autoridad_id": autoridad.id, "estatus": "A"}),
            titulo=f"V.P. de Sentencias de {autoridad.distrito.nombre_corto}, {autoridad.descripcion_corta}",
            estatus="A",
            # form=form,
        )
    # Ninguno de los anteriores
    return redirect(url_for("sentencias.list_distritos"))


@sentencias.route("/sentencias/inactivos")
@permission_required(MODULO, Permiso.ADMINISTRAR)
def list_inactive():
    """Listado de Sentencias inactivos"""
    # Si es administrador ve todo
    if current_user.can_admin("SENTENCIAS"):
        return render_template(
            "sentencias/list_admin.jinja2",
            autoridad=None,
            filtros=json.dumps({"estatus": "B"}),
            titulo="Todas las V.P. de Sentencias inactivas",
            estatus="B",
            form=None,
        )
    # Si es jurisdiccional ve lo de su autoridad
    if current_user.autoridad.es_jurisdiccional:
        autoridad = current_user.autoridad
        return render_template(
            "sentencias/list.jinja2",
            autoridad=autoridad,
            filtros=json.dumps({"autoridad_id": autoridad.id, "estatus": "B"}),
            titulo=f"V.P. de Sentencias inactivas de {autoridad.distrito.nombre_corto}, {autoridad.descripcion_corta}",
            estatus="B",
            form=None,
        )
    # No es jurisdiccional, se redirige al listado de distritos
    return redirect(url_for("sentencias.list_distritos"))


@sentencias.route("/sentencias/distritos")
def list_distritos():
    """Listado de Distritos"""
    return render_template(
        "sentencias/list_distritos.jinja2",
        distritos=Distrito.query.filter_by(es_distrito_judicial=True).filter_by(estatus="A").order_by(Distrito.nombre).all(),
    )


@sentencias.route("/sentencias/distrito/<int:distrito_id>")
def list_autoridades(distrito_id):
    """Listado de Autoridades de un distrito"""
    distrito = Distrito.query.get_or_404(distrito_id)
    return render_template(
        "sentencias/list_autoridades.jinja2",
        distrito=distrito,
        autoridades=Autoridad.query.filter(Autoridad.distrito == distrito)
        .filter_by(es_jurisdiccional=True)
        .filter_by(es_notaria=False)
        .filter_by(estatus="A")
        .order_by(Autoridad.clave)
        .all(),
    )


@sentencias.route("/sentencias/autoridad/<int:autoridad_id>")
def list_autoridad_sentencias(autoridad_id):
    """Listado de Sentencias activas de una autoridad"""
    autoridad = Autoridad.query.get_or_404(autoridad_id)
    form = None
    plantilla = "sentencias/list.jinja2"
    if current_user.can_admin("SENTENCIAS") or set(current_user.get_roles()).intersection(set(ROL_REPORTES_TODOS)):
        plantilla = "sentencias/list_admin.jinja2"
        # form = SentenciaReportForm()
        # form.autoridad_id.data = autoridad.id  # Oculto la autoridad que esta viendo
        # form.fecha_desde.data = datetime.date.today().replace(day=1)  # Por defecto fecha_desde es el primer dia del mes actual
        # form.fecha_hasta.data = datetime.date.today()  # Por defecto fecha_hasta es hoy
    return render_template(
        plantilla,
        autoridad=autoridad,
        filtros=json.dumps({"autoridad_id": autoridad.id, "estatus": "A"}),
        titulo=f"V.P. de Sentencias de {autoridad.distrito.nombre_corto}, {autoridad.descripcion_corta}",
        estatus="A",
        form=form,
    )


@sentencias.route("/sentencias/inactivos/autoridad/<int:autoridad_id>")
@permission_required(MODULO, Permiso.ADMINISTRAR)
def list_autoridad_sentencias_inactive(autoridad_id):
    """Listado de Sentencias inactivas de una autoridad"""
    autoridad = Autoridad.query.get_or_404(autoridad_id)
    if current_user.can_admin("SENTENCIAS"):
        plantilla = "sentencias/list_admin.jinja2"
    else:
        plantilla = "sentencias/list.jinja2"
    return render_template(
        plantilla,
        autoridad=autoridad,
        filtros=json.dumps({"autoridad_id": autoridad.id, "estatus": "B"}),
        titulo=f"V.P. de Sentencias inactivas de {autoridad.distrito.nombre_corto}, {autoridad.descripcion_corta}",
        estatus="B",
        form=None,
    )


@sentencias.route("/sentencias/descargar", methods=["GET"])
@permission_required(MODULO, Permiso.ADMINISTRAR)
def download():
    """Descargar archivo desde Google Cloud Storage"""
    url = request.args.get("url")
    try:
        # Obtener nombre del blob
        blob_name = get_blob_name_from_url(url)
        # Obtener tipo de media
        media_type = get_media_type_from_filename(blob_name)
        # Obtener archivo
        archivo = get_file_from_gcs(current_app.config["CLOUD_STORAGE_DEPOSITO_SENTENCIAS"], blob_name)
    except MyAnyError as error:
        flash(str(error), "warning")
        return redirect(url_for("sentencias.list_active"))
    # Entregar archivo
    return current_app.response_class(archivo, mimetype=media_type)


@sentencias.route("/sentencias/<int:sentencia_id>")
def detail(sentencia_id):
    """Detalle de un Sentencia"""
    sentencia = Sentencia.query.get_or_404(sentencia_id)
    return render_template("sentencias/detail.jinja2", sentencia=sentencia)
