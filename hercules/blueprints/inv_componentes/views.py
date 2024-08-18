"""
Inventarios Componentes, vistas
"""

import json

from flask import Blueprint, flash, redirect, render_template, request, url_for
from flask_login import current_user, login_required

from hercules.blueprints.bitacoras.models import Bitacora
from hercules.blueprints.inv_componentes.models import InvComponente
from hercules.blueprints.modulos.models import Modulo
from hercules.blueprints.permisos.models import Permiso
from hercules.blueprints.usuarios.decorators import permission_required
from lib.datatables import get_datatable_parameters, output_datatable_json
from lib.safe_string import safe_message, safe_string

MODULO = "INV COMPONENTES"

inv_componentes = Blueprint("inv_componentes", __name__, template_folder="templates")


@inv_componentes.before_request
@login_required
@permission_required(MODULO, Permiso.VER)
def before_request():
    """Permiso por defecto"""


@inv_componentes.route("/inv_componentes/datatable_json", methods=["GET", "POST"])
def datatable_json():
    """DataTable JSON para listado de Componentes"""
    # Tomar parámetros de Datatables
    draw, start, rows_per_page = get_datatable_parameters()
    # Consultar
    consulta = InvComponente.query
    # Primero filtrar por columnas propias
    if "estatus" in request.form:
        consulta = consulta.filter_by(estatus=request.form["estatus"])
    else:
        consulta = consulta.filter_by(estatus="A")
    if "inv_categoria_id" in request.form:
        consulta = consulta.filter_by(inv_categoria_id=request.form["inv_categoria_id"])
    if "inv_equipo_id" in request.form:
        consulta = consulta.filter_by(inv_equipo_id=request.form["inv_equipo_id"])
    if "descripcion" in request.form:
        descripcion = safe_string(request.form["descripcion"])
        if descripcion != "":
            consulta = consulta.filter(InvComponente.descripcion.contains(descripcion))
    # Ordenar y paginar
    registros = consulta.order_by(InvComponente.id).offset(start).limit(rows_per_page).all()
    total = consulta.count()
    # Elaborar datos para DataTable
    data = []
    for resultado in registros:
        data.append(
            {
                "detalle": {
                    "id": resultado.id,
                    "url": url_for("inv_componentes.detail", inv_componente_id=resultado.id),
                },
                "inv_categoria": {
                    "nombre": resultado.inv_categoria.nombre,
                    "url": (
                        url_for("inv_categorias.detail", inv_categoria_id=resultado.inv_categoria_id)
                        if current_user.can_view("INV CATEGORIAS")
                        else ""
                    ),
                },
                "descripcion": resultado.descripcion,
                "cantidad": resultado.cantidad,
                "generacion": resultado.generacion,
                "version": resultado.version,
            }
        )
    # Entregar JSON
    return output_datatable_json(draw, total, data)


@inv_componentes.route("/inv_componentes")
def list_active():
    """Listado de Componentes activos"""
    return render_template(
        "inv_componentes/list.jinja2",
        filtros=json.dumps({"estatus": "A"}),
        titulo="Componentes",
        estatus="A",
    )


@inv_componentes.route("/inv_componentes/inactivos")
@permission_required(MODULO, Permiso.ADMINISTRAR)
def list_inactive():
    """Listado de Componentes inactivos"""
    return render_template(
        "inv_componentes/list.jinja2",
        filtros=json.dumps({"estatus": "B"}),
        titulo="Componentes inactivos",
        estatus="B",
    )


@inv_componentes.route("/inv_componentes/<int:inv_componente_id>")
def detail(inv_componente_id):
    """Detalle de un Componente"""
    inv_componente = InvComponente.query.get_or_404(inv_componente_id)
    return render_template("inv_componentes/detail.jinja2", inv_componente=inv_componente)