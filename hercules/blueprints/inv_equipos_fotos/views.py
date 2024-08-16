"""
Inventarios Equipos Fotos, vistas
"""

import json

from flask import Blueprint, flash, redirect, render_template, request, url_for
from flask_login import current_user, login_required

from hercules.blueprints.bitacoras.models import Bitacora
from hercules.blueprints.inv_equipos_fotos.models import InvEquipoFoto
from hercules.blueprints.modulos.models import Modulo
from hercules.blueprints.permisos.models import Permiso
from hercules.blueprints.usuarios.decorators import permission_required
from lib.datatables import get_datatable_parameters, output_datatable_json
from lib.safe_string import safe_message, safe_string

MODULO = "INV EQUIPOS FOTOS"

inv_equipos_fotos = Blueprint("inv_equipos_fotos", __name__, template_folder="templates")


@inv_equipos_fotos.before_request
@login_required
@permission_required(MODULO, Permiso.VER)
def before_request():
    """Permiso por defecto"""


@inv_equipos_fotos.route("/inv_equipos_fotos/datatable_json", methods=["GET", "POST"])
def datatable_json():
    """DataTable JSON para listado de Fotos de Equipos"""
    # Tomar parámetros de Datatables
    draw, start, rows_per_page = get_datatable_parameters()
    # Consultar
    consulta = InvEquipoFoto.query
    # Primero filtrar por columnas propias
    if "estatus" in request.form:
        consulta = consulta.filter_by(estatus=request.form["estatus"])
    else:
        consulta = consulta.filter_by(estatus="A")
    if "inv_equipo_id" in request.form:
        consulta = consulta.filter_by(inv_equipo_id=request.form["inv_equipo_id"])
    if "descripcion" in request.form:
        descripcion = safe_string(request.form["descripcion"])
        if descripcion != "":
            consulta = consulta.filter(InvEquipoFoto.descripcion.contains(descripcion))
    # Ordenar y paginar
    registros = consulta.order_by(InvEquipoFoto.id).offset(start).limit(rows_per_page).all()
    total = consulta.count()
    # Elaborar datos para DataTable
    data = []
    for resultado in registros:
        data.append(
            {
                "detalle": {
                    "archivo": resultado.archivo,
                    "url": url_for("inv_equipos_fotos.detail", inv_equipo_foto_id=resultado.id),
                },
                "descripcion": resultado.descripcion,
            }
        )
    # Entregar JSON
    return output_datatable_json(draw, total, data)


@inv_equipos_fotos.route("/inv_equipos_fotos")
def list_active():
    """Listado de Fotos de Equipos activas"""
    return render_template(
        "inv_equipos_fotos/list.jinja2",
        filtros=json.dumps({"estatus": "A"}),
        titulo="Fotos de Equipos",
        estatus="A",
    )


@inv_equipos_fotos.route("/inv_equipos_fotos/inactivos")
@permission_required(MODULO, Permiso.ADMINISTRAR)
def list_inactive():
    """Listado de Fotos de Equipos inactivas"""
    return render_template(
        "inv_equipos_fotos/list.jinja2",
        filtros=json.dumps({"estatus": "B"}),
        titulo="Fotos de Equipos inactivas",
        estatus="B",
    )


@inv_equipos_fotos.route("/inv_equipos_fotos/<int:inv_equipo_foto_id>")
def detail(inv_equipo_foto_id):
    """Detalle de una Fotos de Equipos"""
    inv_equipo_foto = InvEquipoFoto.query.get_or_404(inv_equipo_foto_id)
    return render_template("inv_equipos_fotos/detail.jinja2", inv_equipo_foto=inv_equipo_foto)
