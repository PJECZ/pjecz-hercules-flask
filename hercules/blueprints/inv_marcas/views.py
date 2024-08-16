"""
Inventarios Marcas, vistas
"""

import json

from flask import Blueprint, flash, redirect, render_template, request, url_for
from flask_login import current_user, login_required

from hercules.blueprints.bitacoras.models import Bitacora
from hercules.blueprints.inv_marcas.models import InvMarca
from hercules.blueprints.modulos.models import Modulo
from hercules.blueprints.permisos.models import Permiso
from hercules.blueprints.usuarios.decorators import permission_required
from lib.datatables import get_datatable_parameters, output_datatable_json
from lib.safe_string import safe_message, safe_string

MODULO = "INV MARCAS"

inv_marcas = Blueprint("inv_marcas", __name__, template_folder="templates")


@inv_marcas.before_request
@login_required
@permission_required(MODULO, Permiso.VER)
def before_request():
    """Permiso por defecto"""


@inv_marcas.route("/inv_marcas/datatable_json", methods=["GET", "POST"])
def datatable_json():
    """DataTable JSON para listado de Marcas"""
    # Tomar parámetros de Datatables
    draw, start, rows_per_page = get_datatable_parameters()
    # Consultar
    consulta = InvMarca.query
    # Primero filtrar por columnas propias
    if "estatus" in request.form:
        consulta = consulta.filter_by(estatus=request.form["estatus"])
    else:
        consulta = consulta.filter_by(estatus="A")
    if "nombre" in request.form:
        nombre = safe_string(request.form["nombre"])
        if nombre != "":
            consulta = consulta.filter(InvMarca.nombre.contains(nombre))
    # Ordenar y paginar
    registros = consulta.order_by(InvMarca.id).offset(start).limit(rows_per_page).all()
    total = consulta.count()
    # Elaborar datos para DataTable
    data = []
    for resultado in registros:
        data.append(
            {
                "detalle": {
                    "nombre": resultado.nombre,
                    "url": url_for("inv_marcas.detail", inv_marca_id=resultado.id),
                },
            }
        )
    # Entregar JSON
    return output_datatable_json(draw, total, data)


@inv_marcas.route("/inv_marcas")
def list_active():
    """Listado de Marcas activas"""
    return render_template(
        "inv_marcas/list.jinja2",
        filtros=json.dumps({"estatus": "A"}),
        titulo="Marcas",
        estatus="A",
    )


@inv_marcas.route("/inv_marcas/inactivos")
@permission_required(MODULO, Permiso.ADMINISTRAR)
def list_inactive():
    """Listado de Marcas inactivas"""
    return render_template(
        "inv_marcas/list.jinja2",
        filtros=json.dumps({"estatus": "B"}),
        titulo="Marcas inactivas",
        estatus="B",
    )


@inv_marcas.route("/inv_marcas/<int:inv_marca_id>")
def detail(inv_marca_id):
    """Detalle de una Marca"""
    inv_marca = InvMarca.query.get_or_404(inv_marca_id)
    return render_template("inv_marcas/detail.jinja2", inv_marca=inv_marca)
