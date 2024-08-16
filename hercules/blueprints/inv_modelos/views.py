"""
Inventarios Modelos, vistas
"""

import json

from flask import Blueprint, flash, redirect, render_template, request, url_for
from flask_login import current_user, login_required

from hercules.blueprints.bitacoras.models import Bitacora
from hercules.blueprints.inv_modelos.models import InvModelo
from hercules.blueprints.modulos.models import Modulo
from hercules.blueprints.permisos.models import Permiso
from hercules.blueprints.usuarios.decorators import permission_required
from lib.datatables import get_datatable_parameters, output_datatable_json
from lib.safe_string import safe_message, safe_string

MODULO = "INV MODELOS"

inv_modelos = Blueprint("inv_modelos", __name__, template_folder="templates")


@inv_modelos.before_request
@login_required
@permission_required(MODULO, Permiso.VER)
def before_request():
    """Permiso por defecto"""


@inv_modelos.route("/inv_modelos/datatable_json", methods=["GET", "POST"])
def datatable_json():
    """DataTable JSON para listado de Modelos"""
    # Tomar parámetros de Datatables
    draw, start, rows_per_page = get_datatable_parameters()
    # Consultar
    consulta = InvModelo.query
    # Primero filtrar por columnas propias
    if "estatus" in request.form:
        consulta = consulta.filter_by(estatus=request.form["estatus"])
    else:
        consulta = consulta.filter_by(estatus="A")
    if "inv_marca_id" in request.form:
        consulta = consulta.filter_by(inv_marca_id=request.form["inv_marca_id"])
    if "descripcion" in request.form:
        descripcion = safe_string(request.form["descripcion"])
        if descripcion != "":
            consulta = consulta.filter(InvModelo.descripcion.contains(descripcion))
    # Ordenar y paginar
    registros = consulta.order_by(InvModelo.id).offset(start).limit(rows_per_page).all()
    total = consulta.count()
    # Elaborar datos para DataTable
    data = []
    for resultado in registros:
        data.append(
            {
                "detalle": {
                    "descripcion": resultado.descripcion,
                    "url": url_for("inv_modelos.detail", inv_modelo_id=resultado.id),
                },
                "marca": {
                    "nombre": resultado.inv_marca.nombre,
                    "url": (
                        url_for("inv_marcas.detail", inv_marca_id=resultado.inv_marca_id)
                        if current_user.can_view("INV MARCAS")
                        else ""
                    ),
                },
            }
        )
    # Entregar JSON
    return output_datatable_json(draw, total, data)


@inv_modelos.route("/inv_modelos")
def list_active():
    """Listado de Modelos activos"""
    return render_template(
        "inv_modelos/list.jinja2",
        filtros=json.dumps({"estatus": "A"}),
        titulo="Modelos",
        estatus="A",
    )


@inv_modelos.route("/inv_modelos/inactivos")
@permission_required(MODULO, Permiso.ADMINISTRAR)
def list_inactive():
    """Listado de Modelos inactivos"""
    return render_template(
        "inv_modelos/list.jinja2",
        filtros=json.dumps({"estatus": "B"}),
        titulo="Modelos inactivos",
        estatus="B",
    )


@inv_modelos.route("/inv_modelos/<int:inv_modelo_id>")
def detail(inv_modelo_id):
    """Detalle de un Modelo"""
    inv_modelo = InvModelo.query.get_or_404(inv_modelo_id)
    return render_template("inv_modelos/detail.jinja2", inv_modelo=inv_modelo)
