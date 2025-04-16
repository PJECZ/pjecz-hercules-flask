"""
Exh Tipos Diligencias, vistas
"""

import json

from flask import Blueprint, flash, redirect, render_template, request, url_for
from flask_login import current_user, login_required

from hercules.blueprints.bitacoras.models import Bitacora
from hercules.blueprints.exh_tipos_diligencias.models import ExhTipoDiligencia
from hercules.blueprints.modulos.models import Modulo
from hercules.blueprints.permisos.models import Permiso
from hercules.blueprints.usuarios.decorators import permission_required
from lib.datatables import get_datatable_parameters, output_datatable_json
from lib.safe_string import safe_clave, safe_message, safe_string

MODULO = "EXH TIPOS DILIGENCIAS"

exh_tipos_diligencias = Blueprint("exh_tipos_diligencias", __name__, template_folder="templates")


@exh_tipos_diligencias.before_request
@login_required
@permission_required(MODULO, Permiso.VER)
def before_request():
    """Permiso por defecto"""


@exh_tipos_diligencias.route("/exh_tipos_diligencias/datatable_json", methods=["GET", "POST"])
def datatable_json():
    """DataTable JSON para listado de Tipos de Diligencias"""
    # Tomar parámetros de Datatables
    draw, start, rows_per_page = get_datatable_parameters()
    # Consultar
    consulta = ExhTipoDiligencia.query
    # Primero filtrar por columnas propias
    if "estatus" in request.form:
        consulta = consulta.filter_by(estatus=request.form["estatus"])
    else:
        consulta = consulta.filter_by(estatus="A")
    if "clave" in request.form:
        clave = safe_clave(request.form["clave"])
        if clave != "":
            consulta = consulta.filter(ExhTipoDiligencia.clave.contains(clave))
    if "descripcion" in request.form:
        descripcion = safe_string(request.form["descripcion"], save_enie=True)
        if descripcion != "":
            consulta = consulta.filter(ExhTipoDiligencia.descripcion.contains(descripcion))
    # Ordenar y paginar
    registros = consulta.order_by(ExhTipoDiligencia.id).offset(start).limit(rows_per_page).all()
    total = consulta.count()
    # Elaborar datos para DataTable
    data = []
    for resultado in registros:
        data.append(
            {
                "detalle": {
                    "clave": resultado.clave,
                    "url": url_for("exh_tipos_diligencias.detail", exh_tipo_diligencia_id=resultado.id),
                },
                "descripcion": resultado.descripcion,
            }
        )
    # Entregar JSON
    return output_datatable_json(draw, total, data)


@exh_tipos_diligencias.route("/exh_tipos_diligencias/select_json", methods=["GET", "POST"])
def select_json():
    """Proporcionar el JSON para elegir con un select tradicional"""
    consulta = ExhTipoDiligencia.query.order_by(ExhTipoDiligencia.nombre)
    data = []
    for resultado in consulta.all():
        data.append(
            {
                "id": resultado.id,
                "nombre": resultado.nombre,
            }
        )
    return json.dumps(data)


@exh_tipos_diligencias.route("/exh_tipos_diligencias")
def list_active():
    """Listado de Tipos de Diligencias activos"""
    return render_template(
        "exh_tipos_diligencias/list.jinja2",
        filtros=json.dumps({"estatus": "A"}),
        titulo="Tipos de Diligencias",
        estatus="A",
    )


@exh_tipos_diligencias.route("/exh_tipos_diligencias/inactivos")
@permission_required(MODULO, Permiso.ADMINISTRAR)
def list_inactive():
    """Listado de Tipos de Diligencias inactivos"""
    return render_template(
        "exh_tipos_diligencias/list.jinja2",
        filtros=json.dumps({"estatus": "B"}),
        titulo="Tipos de Diligencias inactivos",
        estatus="B",
    )


@exh_tipos_diligencias.route("/exh_tipos_diligencias/<int:exh_tipo_diligencia_id>")
def detail(exh_tipo_diligencia_id):
    """Detalle de un Tipo de Diligencia"""
    exh_tipo_diligencia = ExhTipoDiligencia.query.get_or_404(exh_tipo_diligencia_id)
    return render_template("exh_tipos_diligencias/detail.jinja2", exh_tipo_diligencia=exh_tipo_diligencia)
