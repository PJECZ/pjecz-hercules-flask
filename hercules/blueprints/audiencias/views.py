"""
Audiencias, vistas
"""

import json

from flask import Blueprint, flash, redirect, render_template, request, url_for
from flask_login import current_user, login_required

from hercules.blueprints.audiencias.models import Audiencia
from hercules.blueprints.autoridades.models import Autoridad
from hercules.blueprints.bitacoras.models import Bitacora
from hercules.blueprints.distritos.models import Distrito
from hercules.blueprints.modulos.models import Modulo
from hercules.blueprints.permisos.models import Permiso
from hercules.blueprints.usuarios.decorators import permission_required
from lib.datatables import get_datatable_parameters, output_datatable_json
from lib.safe_string import safe_message, safe_string

MODULO = "AUDIENCIAS"

audiencias = Blueprint("audiencias", __name__, template_folder="templates")


def plantilla_por_categoria(categoria: str, prefijo: str = "list_", sufijo: str = "", por_defecto: str = "list"):
    """Determinar la plantilla por tipo de agenda de audiencia"""
    if categoria == "CIVIL FAMILIAR MERCANTIL LETRADO TCYA":
        nombre = f"{prefijo}generica{sufijo}"
    elif categoria == "MATERIA ACUSATORIO PENAL ORAL":
        nombre = f"{prefijo}mapo{sufijo}"
    elif categoria == "DISTRITALES":
        nombre = f"{prefijo}dipe{sufijo}"
    elif categoria == "SALAS":
        nombre = f"{prefijo}sape{sufijo}"
    else:
        nombre = por_defecto
    return f"audiencias/{nombre}.jinja2"


@audiencias.before_request
@login_required
@permission_required(MODULO, Permiso.VER)
def before_request():
    """Permiso por defecto"""


@audiencias.route("/audiencias/datatable_json", methods=["GET", "POST"])
def datatable_json():
    """DataTable JSON para listado de Audiencias"""
    # Tomar parámetros de Datatables
    draw, start, rows_per_page = get_datatable_parameters()
    # Consultar
    consulta = Audiencia.query
    # Primero filtrar por columnas propias
    if "estatus" in request.form:
        consulta = consulta.filter_by(estatus=request.form["estatus"])
    else:
        consulta = consulta.filter_by(estatus="A")
    if "autoridad_id" in request.form:
        autoridad = Autoridad.query.get(request.form["autoridad_id"])
        if autoridad:
            consulta = consulta.filter_by(autoridad=autoridad)
    # Ordenar y paginar
    registros = consulta.order_by(Audiencia.tiempo.desc()).offset(start).limit(rows_per_page).all()
    total = consulta.count()
    # Elaborar datos para DataTable
    data = []
    for resultado in registros:
        data.append(
            {
                "detalle": {
                    "tiempo": resultado.tiempo.strftime("%Y-%m-%d %H:%M"),
                    "url": url_for("audiencias.detail", audiencia_id=resultado.id),
                },
                "tipo_audiencia": resultado.tipo_audiencia,
                "expediente": resultado.expediente,
                "actores": resultado.actores,
                "demandados": resultado.demandados,
                "sala": resultado.sala,
                "caracter": resultado.caracter,
                "causa_penal": resultado.causa_penal,
                "delitos": resultado.delitos,
                "toca": resultado.toca,
                "expediente_origen": resultado.expediente_origen,
                "imputados": resultado.imputados,
                "origen": resultado.origen,
            }
        )
    # Entregar JSON
    return output_datatable_json(draw, total, data)


@audiencias.route("/audiencias/datatable_json_admin", methods=["GET", "POST"])
def datatable_json_admin():
    """DataTable JSON para listado de Audiencias"""
    # Tomar parámetros de Datatables
    draw, start, rows_per_page = get_datatable_parameters()
    # Consultar
    consulta = Audiencia.query
    # Primero filtrar por columnas propias
    if "estatus" in request.form:
        consulta = consulta.filter_by(estatus=request.form["estatus"])
    else:
        consulta = consulta.filter_by(estatus="A")
    if "autoridad_id" in request.form:
        autoridad = Autoridad.query.get(request.form["autoridad_id"])
        if autoridad:
            consulta = consulta.filter_by(autoridad=autoridad)
    # Ordenar y paginar
    registros = consulta.order_by(Audiencia.id).offset(start).limit(rows_per_page).all()
    total = consulta.count()
    # Elaborar datos para DataTable
    data = []
    for resultado in registros:
        data.append(
            {
                "creado": resultado.creado.strftime("%Y-%m-%d %H:%M:%S"),
                "autoridad": resultado.autoridad.clave,
                "detalle": {
                    "tiempo": resultado.tiempo.strftime("%Y-%m-%d %H:%M"),
                    "url": url_for("audiencias.detail", audiencia_id=resultado.id),
                },
                "tipo_audiencia": resultado.tipo_audiencia,
                "expediente": resultado.expediente,
                "actores": resultado.actores,
                "demandados": resultado.demandados,
                "sala": resultado.sala,
                "caracter": resultado.caracter,
                "causa_penal": resultado.causa_penal,
                "delitos": resultado.delitos,
                "toca": resultado.toca,
                "expediente_origen": resultado.expediente_origen,
                "imputados": resultado.imputados,
                "origen": resultado.origen,
            }
        )
    # Entregar JSON
    return output_datatable_json(draw, total, data)


@audiencias.route("/audiencias")
def list_active():
    """Listado de Audiencias activos"""
    # Si es administrador ve todo
    if current_user.can_admin("AUDIENCIAS"):
        return render_template(
            "audiencias/list_admin.jinja2",
            autoridad=None,
            filtros=json.dumps({"estatus": "A"}),
            titulo="Todos las Audiencias",
            estatus="A",
        )
    # Si es jurisdiccional ve lo de su autoridad
    if current_user.autoridad.es_jurisdiccional:
        autoridad = current_user.autoridad
        return render_template(
            plantilla_por_categoria(autoridad.audiencia_categoria, por_defecto="list"),
            autoridad=autoridad,
            filtros=json.dumps({"autoridad_id": autoridad.id, "estatus": "A"}),
            titulo=f"Audiencias de {autoridad.distrito.nombre_corto}, {autoridad.descripcion_corta}",
            estatus="A",
        )
    # Ninguno de los anteriores
    return redirect(url_for("audiencias.list_distritos"))


@audiencias.route("/audiencias/inactivos")
@permission_required(MODULO, Permiso.ADMINISTRAR)
def list_inactive():
    """Listado de Audiencias inactivos"""
    # Si es administrador ve todo
    if current_user.can_admin("AUDIENCIAS"):
        return render_template(
            "audiencias/list_admin.jinja2",
            autoridad=None,
            filtros=json.dumps({"estatus": "B"}),
            titulo="Todos las Audiencias inactivos",
            estatus="B",
        )
    # Si es jurisdiccional ve lo de su autoridad
    if current_user.autoridad.es_jurisdiccional:
        autoridad = current_user.autoridad
        return render_template(
            plantilla_por_categoria(autoridad.audiencia_categoria, por_defecto="list"),
            autoridad=autoridad,
            filtros=json.dumps({"autoridad_id": autoridad.id, "estatus": "B"}),
            titulo=f"Audiencias inactivas de {autoridad.distrito.nombre_corto}, {autoridad.descripcion_corta}",
            estatus="B",
        )
    # Ninguno de los anteriores
    return redirect(url_for("audiencias.list_distritos"))


@audiencias.route("/audiencias/distritos")
def list_distritos():
    """Listado de Distritos"""
    return render_template(
        "audiencias/list_distritos.jinja2",
        distritos=Distrito.query.filter_by(es_distrito_judicial=True).filter_by(estatus="A").order_by(Distrito.nombre).all(),
    )


@audiencias.route("/audiencias/distrito/<int:distrito_id>")
def list_autoridades(distrito_id):
    """Listado de Autoridades de un distrito"""
    distrito = Distrito.query.get_or_404(distrito_id)
    return render_template(
        "audiencias/list_autoridades.jinja2",
        distrito=distrito,
        autoridades=Autoridad.query.filter(Autoridad.distrito == distrito)
        .filter_by(es_jurisdiccional=True)
        .filter_by(es_notaria=False)
        .filter_by(estatus="A")
        .order_by(Autoridad.clave)
        .all(),
    )


@audiencias.route("/audiencias/autoridad/<int:autoridad_id>")
def list_autoridad_audiencias(autoridad_id):
    """Listado de Audiencias activas de una autoridad"""
    autoridad = Autoridad.query.get_or_404(autoridad_id)
    if current_user.can_admin("AUDIENCIAS"):
        plantilla = plantilla_por_categoria(autoridad.audiencia_categoria, sufijo="_admin", por_defecto="list_admin")
    else:
        plantilla = plantilla_por_categoria(autoridad.audiencia_categoria, por_defecto="list")
    return render_template(
        plantilla,
        autoridad=autoridad,
        filtros=json.dumps({"autoridad_id": autoridad.id, "estatus": "A"}),
        titulo=f"Audiencias de {autoridad.distrito.nombre_corto}, {autoridad.descripcion_corta}",
        estatus="A",
    )


@audiencias.route("/audiencias/inactivos/autoridad/<int:autoridad_id>")
@permission_required(MODULO, Permiso.ADMINISTRAR)
def list_autoridad_audiencias_inactive(autoridad_id):
    """Listado de Audiencias inactivas de una autoridad"""
    autoridad = Autoridad.query.get_or_404(autoridad_id)
    if current_user.can_admin("AUDIENCIAS"):
        plantilla = plantilla_por_categoria(autoridad.audiencia_categoria, sufijo="_admin", por_defecto="list_admin")
    else:
        plantilla = plantilla_por_categoria(autoridad.audiencia_categoria, por_defecto="list")
    return render_template(
        plantilla,
        autoridad=autoridad,
        filtros=json.dumps({"autoridad_id": autoridad.id, "estatus": "B"}),
        titulo=f"Audiencias inactivas de {autoridad.distrito.nombre_corto}, {autoridad.descripcion_corta}",
        estatus="B",
    )


@audiencias.route("/audiencias/<int:audiencia_id>")
def detail(audiencia_id):
    """Detalle de un Audiencia"""
    audiencia = Audiencia.query.get_or_404(audiencia_id)
    return render_template("audiencias/detail.jinja2", audiencia=audiencia)


# @audiencias.route("/audiencias/nuevo/generica", methods=["GET", "POST"])
# @permission_required(MODULO, Permiso.CREAR)
# def new_generica():
#     """Nueva Audiencia Materias CIVIL FAMILIAR MERCANTIL LETRADO TCYA"""

#     # Validar autoridad
#     autoridad = current_user.autoridad
#     if autoridad.estatus != "A":
#         flash("El juzgado/autoridad no es activa.", "warning")
#         return redirect(url_for("audiencias.list_active"))
#     if autoridad.audiencia_categoria != "CIVIL FAMILIAR MERCANTIL LETRADO TCYA":
#         flash("La categoría de audiencia no es CIVIL FAMILIAR MERCANTIL LETRADO TCYA.", "warning")
#         return redirect(url_for("audiencias.list_active"))

#     # Si viene el formulario
#     form = AudienciaGenericaForm()
#     if form.validate_on_submit():

#         # Definir tiempo con la fecha y horas:minutos
#         try:
#             tiempo = f"{form.tiempo_fecha.data} {form.tiempo_horas_minutos.data}"
#             tiempo = datetime.strptime(tiempo, "%Y-%m-%d %H:%M:%S")
#             tiempo_mensaje = join_for_message(form.tiempo_fecha.data, form.tiempo_horas_minutos.data)
#         except ValueError as error:
#             flash(str(error), "warning")
#             return render_template("audiencias/new_generica.jinja2", form=form)

#         # Validar tipo de audiencia
#         tipo_audiencia = safe_string(form.tipo_audiencia.data)
#         if tipo_audiencia == "":
#             tipo_audiencia = "NO DEFINIDO"

#         # Validar expediente
#         try:
#             expediente = safe_expediente(form.expediente.data)
#         except (IndexError, ValueError):
#             flash("El expediente es incorrecto.", "warning")
#             return render_template("audiencias/new_generica.jinja2", form=form)

#         # Insertar registro
#         audiencia = Audiencia(
#             autoridad=autoridad,
#             tiempo=tiempo,
#             tipo_audiencia=tipo_audiencia,
#             expediente=expediente,
#             actores=safe_string(form.actores.data),
#             demandados=safe_string(form.demandados.data),
#         )
#         audiencia.save()

#         # Mostrar mensaje de éxito e ir al detalle
#         bitacora = Bitacora(
#             modulo=Modulo.query.filter_by(nombre=MODULO).first(),
#             usuario=current_user,
#             descripcion=safe_message(f"Nueva audiencia en {autoridad.clave} para {tiempo_mensaje}"),
#             url=url_for("audiencias.detail", audiencia_id=audiencia.id),
#         )
#         bitacora.save()
#         flash(bitacora.descripcion, "success")
#         return redirect(bitacora.url)

#     # Prellenado del formulario
#     form.distrito.data = autoridad.distrito.nombre
#     form.autoridad.data = autoridad.descripcion
#     return render_template("audiencias/new_generica.jinja2", form=form)
