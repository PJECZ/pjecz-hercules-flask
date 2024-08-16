"""
Inventarios Categorias, vistas
"""

import json

from flask import Blueprint, flash, redirect, render_template, request, url_for
from flask_login import current_user, login_required

from hercules.blueprints.bitacoras.models import Bitacora
from hercules.blueprints.inv_categorias.models import InvCategoria
from hercules.blueprints.modulos.models import Modulo
from hercules.blueprints.permisos.models import Permiso
from hercules.blueprints.usuarios.decorators import permission_required
from lib.datatables import get_datatable_parameters, output_datatable_json
from lib.safe_string import safe_message, safe_string

MODULO = "INV CATEGORIAS"

inv_categorias = Blueprint("inv_categorias", __name__, template_folder="templates")


@inv_categorias.before_request
@login_required
@permission_required(MODULO, Permiso.VER)
def before_request():
    """Permiso por defecto"""


@inv_categorias.route("/inv_categorias/datatable_json", methods=["GET", "POST"])
def datatable_json():
    """DataTable JSON para listado de InvCategorias"""
    # Tomar parámetros de Datatables
    draw, start, rows_per_page = get_datatable_parameters()
    # Consultar
    consulta = InvCategoria.query
    # Primero filtrar por columnas propias
    if "estatus" in request.form:
        consulta = consulta.filter_by(estatus=request.form["estatus"])
    else:
        consulta = consulta.filter_by(estatus="A")
    # Luego filtrar por columnas de otras tablas
    if "nombre" in request.form:
        nombre = safe_string(request.form["nombre"])
        if nombre != "":
            consulta = consulta.filter(InvCategoria.nombre.contains(nombre))
    # Ordenar y paginar
    registros = consulta.order_by(InvCategoria.id).offset(start).limit(rows_per_page).all()
    total = consulta.count()
    # Elaborar datos para DataTable
    data = []
    for resultado in registros:
        data.append(
            {
                "detalle": {
                    "nombre": resultado.nombre,
                    "url": url_for("inv_categorias.detail", inv_categoria_id=resultado.id),
                },
            }
        )
    # Entregar JSON
    return output_datatable_json(draw, total, data)


@inv_categorias.route("/inv_categorias")
def list_active():
    """Listado de Categorias activas"""
    return render_template(
        "inv_categorias/list.jinja2",
        filtros=json.dumps({"estatus": "A"}),
        titulo="Categorias",
        estatus="A",
    )


@inv_categorias.route("/inv_categorias/inactivos")
@permission_required(MODULO, Permiso.ADMINISTRAR)
def list_inactive():
    """Listado de Categorias inactivas"""
    return render_template(
        "inv_categorias/list.jinja2",
        filtros=json.dumps({"estatus": "B"}),
        titulo="Categorias inactivas",
        estatus="B",
    )


@inv_categorias.route("/inv_categorias/<int:inv_categoria_id>")
def detail(inv_categoria_id):
    """Detalle de una Categoria"""
    inv_categoria = InvCategoria.query.get_or_404(inv_categoria_id)
    return render_template("inv_categorias/detail.jinja2", inv_categoria=inv_categoria)
