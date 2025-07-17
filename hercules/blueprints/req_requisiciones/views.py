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
from hercules.blueprints.usuarios.models import Usuario


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
        consulta = consulta.filter(ReqRequisicion.estatus == request.form["estatus"])
    else:
        consulta = consulta.filter(ReqRequisicion.estatus == "A")
    # Filtrar por ID de autoridad
    if "autoridad_id" in request.form:
        autoridad_id = int(request.form["autoridad_id"])
        if autoridad_id:
            consulta = consulta.join(Usuario)
            consulta = consulta.filter(Usuario.autoridad_id == autoridad_id)
    # Ordenar y paginar
    registros = consulta.order_by(ReqRequisicion.creado.desc()).offset(start).limit(rows_per_page).all()
    total = consulta.count()
    # Elaborar datos para DataTable
    data = []
    for resultado in registros:
        data.append(
            {
                "detalle": {
                    "id": resultado.id,
                    "url": url_for("req_requisiciones.detail", req_requisicion_id=resultado.id),
                },
                "fecha": resultado.fecha.strftime("%Y-%m-%d"),
                "usuario": {
                    "nombre": resultado.usuario.nombre,
                    "url": url_for("usuarios.detail", usuario_id=resultado.usuario.id),
                },
                "estado": resultado.estado,
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
        titulo="Mis Requisiciones",
        estatus="A",
    )


@req_requisiciones.route("/req_requisiciones_mi_autoridad")
def list_active_mi_autoridad():
    """Listado de Req Requisiciones de mi autoridad activos"""
    return render_template(
        "req_requisiciones/list.jinja2",
        filtros=json.dumps({"estatus": "A", "autoridad_id": current_user.autoridad.id}),
        titulo="Requisiciones de mi Autoridad",
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


@req_requisiciones.route("/req_requisiciones/<req_requisicion_id>")
def detail(req_requisicion_id):
    """Detalle de un Req Requisición"""
    req_requisicion = ReqRequisicion.query.get_or_404(req_requisicion_id)
    return render_template("req_requisiciones/detail.jinja2", req_requisicion=req_requisicion)


@req_requisiciones.route("/req_requisiciones/nuevo", methods=["GET", "POST"])
@permission_required(MODULO, Permiso.CREAR)
def new():
    """Nuevo Req Requisición"""
    return render_template("req_requisiciones/new.jinja2", form=form)
