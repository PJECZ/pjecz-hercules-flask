"""
Inventarios Redes, vistas
"""

import json

from flask import Blueprint, flash, redirect, render_template, request, url_for
from flask_login import current_user, login_required

from hercules.blueprints.bitacoras.models import Bitacora
from hercules.blueprints.inv_redes.models import InvRed
from hercules.blueprints.modulos.models import Modulo
from hercules.blueprints.permisos.models import Permiso
from hercules.blueprints.usuarios.decorators import permission_required
from lib.datatables import get_datatable_parameters, output_datatable_json
from lib.safe_string import safe_message, safe_string

MODULO = "INV REDES"

inv_redes = Blueprint("inv_redes", __name__, template_folder="templates")


@inv_redes.before_request
@login_required
@permission_required(MODULO, Permiso.VER)
def before_request():
    """Permiso por defecto"""


@inv_redes.route("/inv_redes/datatable_json", methods=["GET", "POST"])
def datatable_json():
    """DataTable JSON para listado de Redes"""
    # Tomar parámetros de Datatables
    draw, start, rows_per_page = get_datatable_parameters()
    # Consultar
    consulta = InvRed.query
    # Primero filtrar por columnas propias
    if "estatus" in request.form:
        consulta = consulta.filter_by(estatus=request.form["estatus"])
    else:
        consulta = consulta.filter_by(estatus="A")
    if "nombre" in request.form:
        nombre = safe_string(request.form["nombre"])
        if nombre != "":
            consulta = consulta.filter(InvRed.nombre.contains(nombre))
    if "tipo" in request.form:
        tipo = safe_string(request.form["tipo"])
        if tipo != "":
            consulta = consulta.filter(InvRed.tipo == tipo)
    # Ordenar y paginar
    registros = consulta.order_by(InvRed.id).offset(start).limit(rows_per_page).all()
    total = consulta.count()
    # Elaborar datos para DataTable
    data = []
    for resultado in registros:
        data.append(
            {
                "detalle": {
                    "nombre": resultado.nombre,
                    "url": url_for("inv_redes.detail", inv_red_id=resultado.id),
                },
            }
        )
    # Entregar JSON
    return output_datatable_json(draw, total, data)


@inv_redes.route("/inv_redes")
def list_active():
    """Listado de Redes activas"""
    return render_template(
        "inv_redes/list.jinja2",
        filtros=json.dumps({"estatus": "A"}),
        titulo="Redes",
        estatus="A",
    )


@inv_redes.route("/inv_redes/inactivos")
@permission_required(MODULO, Permiso.ADMINISTRAR)
def list_inactive():
    """Listado de Redes inactivas"""
    return render_template(
        "inv_redes/list.jinja2",
        filtros=json.dumps({"estatus": "B"}),
        titulo="Redes inactivas",
        estatus="B",
    )


@inv_redes.route("/inv_redes/<int:inv_red_id>")
def detail(inv_red_id):
    """Detalle de una Red"""
    inv_red = InvRed.query.get_or_404(inv_red_id)
    return render_template("inv_redes/detail.jinja2", inv_red=inv_red)
