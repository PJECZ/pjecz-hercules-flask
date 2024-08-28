"""
Edictos Acuses, vistas
"""

import json

from flask import Blueprint, render_template, request, url_for
from flask_login import login_required

from hercules.blueprints.edictos_acuses.models import EdictoAcuse
from hercules.blueprints.permisos.models import Permiso
from hercules.blueprints.usuarios.decorators import permission_required
from lib.datatables import get_datatable_parameters, output_datatable_json

MODULO = "EDICTOS ACUSES"

edictos_acuses = Blueprint("edictos_acuses", __name__, template_folder="templates")


@edictos_acuses.before_request
@login_required
@permission_required(MODULO, Permiso.VER)
def before_request():
    """Permiso por defecto"""


@edictos_acuses.route("/edictos_acuses/datatable_json", methods=["GET", "POST"])
def datatable_json():
    """DataTable JSON para listado de Edicto Acuse"""
    # Tomar parámetros de Datatables
    draw, start, rows_per_page = get_datatable_parameters()
    # Consultar
    consulta = EdictoAcuse.query
    # Primero filtrar por columnas propias
    if "estatus" in request.form:
        consulta = consulta.filter_by(estatus=request.form["estatus"])
    else:
        consulta = consulta.filter_by(estatus="A")
    if "edicto_id" in request.form:
        consulta = consulta.filter_by(edicto_id=request.form["edicto_id"])
    # Ordenar y paginar
    registros = consulta.order_by(EdictoAcuse.id).offset(start).limit(rows_per_page).all()
    total = consulta.count()
    # Elaborar datos para DataTable
    data = []
    for resultado in registros:
        data.append(
            {
                "detalle": {
                    "fecha": resultado.fecha,
                    "url": url_for("edictos_acuses.detail", edicto_acuse_id=resultado.id),
                },
                "edicto_descripcion": resultado.edicto.descripcion,
                "edicto_expediente": resultado.edicto.expediente,
            }
        )
    # Entregar JSON
    return output_datatable_json(draw, total, data)


@edictos_acuses.route("/edictos_acuses")
def list_active():
    """Listado de Edictos Acuses activos"""
    return render_template(
        "edictos_acuses/list.jinja2",
        filtros=json.dumps({"estatus": "A"}),
        titulo="Edictos Acuses",
        estatus="A",
    )


@edictos_acuses.route("/edictos_acuses/inactivos")
@permission_required(MODULO, Permiso.ADMINISTRAR)
def list_inactive():
    """Listado de Edictos Acuses inactivos"""
    return render_template(
        "edictos_acuses/list.jinja2",
        filtros=json.dumps({"estatus": "B"}),
        titulo="Edictos Acuses inactivos",
        estatus="B",
    )


@edictos_acuses.route("/edictos_acuses/<int:edicto_acuse_id>")
def detail(edicto_acuse_id):
    """Detalle de un Edicto Acuse"""
    edicto_acuse = EdictoAcuse.query.get_or_404(edicto_acuse_id)
    return render_template("edictos_acuses/detail.jinja2", edicto_acuse=edicto_acuse)
