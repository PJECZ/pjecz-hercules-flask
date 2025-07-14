"""
Req Requisiciones, vistas
"""

import json
from flask import Blueprint, flash, redirect, render_template, request, url_for
from flask_login import current_user, login_required

from lib.datatables import get_datatable_parameters, output_datatable_json
from lib.safe_string import safe_string, safe_message

from hercules.blueprints.bitacoras.models import Bitacora
from hercules.blueprints.modulos.models import Modulo
from hercules.blueprints.permisos.models import Permiso
from hercules.blueprints.usuarios.decorators import permission_required
from hercules.blueprints.req_requisiciones.models import ReqRequisicion

# Roles necesarios
ROL_LECTOR = "REQUISICIONES LECTOR"
ROL_ESCRITOR = "REQUISICIONES ESCRITOR"
ROL_SOLICITANTE = "REQUISICIONES SOLICITANTE"
ROL_AUTORIZANTE = "REQUISICIONES AUTORIZANTE"
ROL_REVISOR = "REQUISICIONES REVISOR"
ROL_MATERIALES = "REQUISICIONES MATERIALES"


MODULO = "REQ REQUISICIONES"

req_requisiciones = Blueprint("req_requisiciones", __name__, template_folder="templates")


@req_requisiciones.before_request
@login_required
@permission_required(MODULO, Permiso.VER)
def before_request():
    """Permiso por defecto"""


@req_requisiciones.route("/req_requisiciones/datatable_json", methods=["GET", "POST"])
def datatable_json():
    """DataTable JSON para listado de Req Requisiciones"""
    # Tomar parámetros de Datatables
    draw, start, rows_per_page = get_datatable_parameters()
    # Consultar
    consulta = ReqRequisicion.query
    # Primero filtrar por columnas propias
    if "estatus" in request.form:
        consulta = consulta.filter_by(estatus=request.form["estatus"])
    else:
        consulta = consulta.filter_by(estatus="A")
    # if "persona_id" in request.form:
    #     consulta = consulta.filter_by(persona_id=request.form["persona_id"])
    # Luego filtrar por columnas de otras tablas
    # if "persona_rfc" in request.form:
    #     consulta = consulta.join(Persona)
    #     consulta = consulta.filter(Persona.rfc.contains(safe_rfc(request.form["persona_rfc"], search_fragment=True)))
    # Ordenar y paginar
    registros = consulta.order_by(ReqRequisicion.id).offset(start).limit(rows_per_page).all()
    total = consulta.count()
    # Elaborar datos para DataTable
    data = []
    for resultado in registros:
        data.append(
            {
                "detalle": {
                    "nombre": resultado.nombre,
                    "url": url_for("req_requisiciones.detail", req_requisicion_id=resultado.id),
                },
            }
        )
    # Entregar JSON
    return output_datatable_json(draw, total, data)


@req_requisiciones.route("/req_requisiciones")
def list_active():
    """Listado de Req Requisiciones activos"""
    return render_template(
        "req_requisiciones/list.jinja2",
        filtros=json.dumps({"estatus": "A"}),
        titulo="Requisiciones",
        estatus="A",
    )


@req_requisiciones.route("/req_requisiciones/inactivos")
@permission_required(MODULO, Permiso.ADMINISTRAR)
def list_inactive():
    """Listado de Req Requisiciones inactivos"""
    return render_template(
        "req_requisiciones/list.jinja2",
        filtros=json.dumps({"estatus": "B"}),
        titulo="Requisiciones inactivas",
        estatus="B",
    )


@req_requisiciones.route("/req_requisiciones/<int:req_requisiciones_id>")
def detail(req_requisiciones_id):
    """Detalle de un Req Requisición"""
    req_requisicion = ReqRequisicion.query.get_or_404(req_requisiciones_id)
    return render_template("req_requisiciones/detail.jinja2", req_requisicion=req_requisicion)
