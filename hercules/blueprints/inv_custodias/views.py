"""
Inventarios Custodias, vistas
"""

import json

from flask import Blueprint, flash, redirect, render_template, request, url_for
from flask_login import current_user, login_required

from hercules.blueprints.bitacoras.models import Bitacora
from hercules.blueprints.inv_custodias.models import InvCustodia
from hercules.blueprints.modulos.models import Modulo
from hercules.blueprints.permisos.models import Permiso
from hercules.blueprints.usuarios.decorators import permission_required
from lib.datatables import get_datatable_parameters, output_datatable_json
from lib.safe_string import safe_message, safe_string

MODULO = "INV CUSTODIAS"

inv_custodias = Blueprint("inv_custodias", __name__, template_folder="templates")


@inv_custodias.before_request
@login_required
@permission_required(MODULO, Permiso.VER)
def before_request():
    """Permiso por defecto"""


@inv_custodias.route("/inv_custodias/datatable_json", methods=["GET", "POST"])
def datatable_json():
    """DataTable JSON para listado de Custodias"""
    # Tomar parámetros de Datatables
    draw, start, rows_per_page = get_datatable_parameters()
    # Consultar
    consulta = InvCustodia.query
    # Primero filtrar por columnas propias
    if "estatus" in request.form:
        consulta = consulta.filter_by(estatus=request.form["estatus"])
    else:
        consulta = consulta.filter_by(estatus="A")
    if "inv_custodia_id" in request.form:
        consulta = consulta.filter_by(id=request.form["inv_custodia_id"])
    else:
        if "usuario_id" in request.form:
            consulta = consulta.filter_by(usuario_id=request.form["usuario_id"])
        if "nombre_completo" in request.form:
            nombre_completo = safe_string(request.form["nombre_completo"])
            if nombre_completo != "":
                consulta = consulta.filter(InvCustodia.nombre_completo.contains(nombre_completo))
    # Ordenar y paginar
    registros = consulta.order_by(InvCustodia.id).offset(start).limit(rows_per_page).all()
    total = consulta.count()
    # Elaborar datos para DataTable
    data = []
    for resultado in registros:
        data.append(
            {
                "detalle": {
                    "id": resultado.id,
                    "url": url_for("inv_custodias.detail", inv_custodia_id=resultado.id),
                },
                "usuario": {
                    "nombre_completo": resultado.nombre_completo,
                    "url": (
                        url_for("usuarios.detail", usuario_id=resultado.usuario_id) if current_user.can_view("USUARIOS") else ""
                    ),
                },
                "fecha": resultado.fecha.strftime("%Y-%m-%d"),
                "equipos_cantidad": resultado.equipos_cantidad if resultado.equipos_cantidad != 0 else "-",
                "equipos_fotos_cantidad": resultado.equipos_fotos_cantidad if resultado.equipos_fotos_cantidad != 0 else "-",
                "oficina": {
                    "clave": resultado.usuario.oficina.clave,
                    "url": (
                        url_for("oficinas.detail", oficina_id=resultado.usuario.oficina_id)
                        if current_user.can_view("OFICINAS")
                        else ""
                    ),
                },
            }
        )
    # Entregar JSON
    return output_datatable_json(draw, total, data)


@inv_custodias.route("/inv_custodias")
def list_active():
    """Listado de Custodias activos"""
    return render_template(
        "inv_custodias/list.jinja2",
        filtros=json.dumps({"estatus": "A"}),
        titulo="Custodias",
        estatus="A",
    )


@inv_custodias.route("/inv_custodias/inactivos")
@permission_required(MODULO, Permiso.ADMINISTRAR)
def list_inactive():
    """Listado de Custodias inactivos"""
    return render_template(
        "inv_custodias/list.jinja2",
        filtros=json.dumps({"estatus": "B"}),
        titulo="Custodias inactivos",
        estatus="B",
    )


@inv_custodias.route("/inv_custodias/<int:inv_custodia_id>")
def detail(inv_custodia_id):
    """Detalle de un Custodia"""
    inv_custodia = InvCustodia.query.get_or_404(inv_custodia_id)
    return render_template("inv_custodias/detail.jinja2", inv_custodia=inv_custodia)
