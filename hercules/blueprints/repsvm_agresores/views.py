"""
REPSVM Agresores, vistas
"""

import json

from flask import Blueprint, flash, redirect, render_template, request, url_for
from flask_login import current_user, login_required

from hercules.blueprints.bitacoras.models import Bitacora
from hercules.blueprints.modulos.models import Modulo
from hercules.blueprints.permisos.models import Permiso
from hercules.blueprints.repsvm_agresores.models import REPSVMAgresor
from hercules.blueprints.usuarios.decorators import permission_required
from lib.datatables import get_datatable_parameters, output_datatable_json
from lib.safe_string import safe_message, safe_string

MODULO = "REPSVM AGRESORES"

repsvm_agresores = Blueprint("repsvm_agresores", __name__, template_folder="templates")


@repsvm_agresores.before_request
@login_required
@permission_required(MODULO, Permiso.VER)
def before_request():
    """Permiso por defecto"""


@repsvm_agresores.route("/repsvm_agresores/datatable_json", methods=["GET", "POST"])
def datatable_json():
    """DataTable JSON para listado de REPSVM Agresores"""
    # Tomar parámetros de Datatables
    draw, start, rows_per_page = get_datatable_parameters()
    # Consultar
    consulta = REPSVMAgresor.query
    # Primero filtrar por columnas propias
    if "estatus" in request.form:
        consulta = consulta.filter_by(estatus=request.form["estatus"])
    else:
        consulta = consulta.filter_by(estatus="A")
    if "distrito_id" in request.form:
        consulta = consulta.filter_by(distrito_id=request.form["distrito_id"])
    if "nombre" in request.form:
        nombre = safe_string(request.form["nombre"])
        if nombre != "":
            consulta = consulta.filter(REPSVMAgresor.nombre.contains(nombre))
    if "numero_causa" in request.form:
        numero_causa = safe_string(request.form["numero_causa"])
        if numero_causa != "":
            consulta = consulta.filter(REPSVMAgresor.numero_causa.contains(numero_causa))
    # Ordenar y paginar
    registros = consulta.order_by(REPSVMAgresor.distrito_id, REPSVMAgresor.nombre).offset(start).limit(rows_per_page).all()
    total = consulta.count()
    # Elaborar datos para DataTable
    data = []
    for resultado in registros:
        data.append(
            {
                "id": resultado.id,
                "detalle": {
                    "nombre": resultado.nombre,
                    "url": url_for("repsvm_agresores.detail", repsvm_agresor_id=resultado.id),
                },
                "distrito": {
                    "nombre_corto": resultado.distrito.nombre_corto,
                    "url": (
                        url_for("distritos.detail", distrito_id=resultado.distrito_id)
                        if current_user.can_view("DISTRITOS")
                        else ""
                    ),
                },
                "change_consecutivo": {
                    "id": resultado.id,
                    "consecutivo": resultado.consecutivo,
                },
                "numero_causa": resultado.numero_causa,
                "pena_impuesta": resultado.pena_impuesta,
                "sentencia_url": resultado.sentencia_url,
                "toggle_es_publico": {
                    "id": resultado.id,
                    "consecutivo": resultado.consecutivo,
                    "es_publico": resultado.es_publico,
                    "url": url_for("repsvm_agresores.toggle_es_publico_json", repsvm_agresor_id=resultado.id),
                },
            }
        )
    # Entregar JSON
    return output_datatable_json(draw, total, data)


@repsvm_agresores.route("/repsvm_agresores/toggle_es_publico/<int:repsvm_agresor_id>", methods=["GET", "POST"])
@permission_required(MODULO, Permiso.MODIFICAR)
def toggle_es_publico_json(repsvm_agresor_id):
    """Cambiar un agresor para que sea publico o privado"""

    # Consultar agresor
    repsvm_agresor = REPSVMAgresor.query.get(repsvm_agresor_id)
    if repsvm_agresor is None:
        return {"success": False, "message": "No encontrado"}

    # Cambiar es_publico a su opuesto
    repsvm_agresor.es_publico = not repsvm_agresor.es_publico

    # Si es publico, definir consecutivo
    if repsvm_agresor.es_publico:
        maximo = (
            REPSVMAgresor.query.filter_by(estatus="A", es_publico=True, distrito_id=repsvm_agresor.distrito_id)
            .order_by(REPSVMAgresor.consecutivo.desc())
            .first()
        )
        if maximo is None:
            repsvm_agresor.consecutivo = 1  # Es el primero de su distrito
        else:
            repsvm_agresor.consecutivo = maximo.consecutivo + 1  # Es el siguiente de su distrito
    else:
        repsvm_agresor.consecutivo = 0  # No es publico, poner consecutivo en cero

    # Guardar
    repsvm_agresor.save()

    # Entregar JSON
    return {
        "success": True,
        "message": "Es publico" if repsvm_agresor.es_publico else "Es privado",
        "consecutivo": repsvm_agresor.consecutivo,
        "es_publico": repsvm_agresor.es_publico,
        "id": repsvm_agresor.id,
    }


@repsvm_agresores.route("/repsvm_agresores")
def list_active():
    """Listado de Agresores activos"""
    return render_template(
        "repsvm_agresores/list.jinja2",
        filtros=json.dumps({"estatus": "A"}),
        titulo="REPSVM Agresores",
        estatus="A",
    )


@repsvm_agresores.route("/repsvm_agresores/inactivos")
@permission_required(MODULO, Permiso.ADMINISTRAR)
def list_inactive():
    """Listado de Agresores inactivos"""
    return render_template(
        "repsvm_agresores/list.jinja2",
        filtros=json.dumps({"estatus": "B"}),
        titulo="REPSVM Agresores inactivos",
        estatus="B",
    )


@repsvm_agresores.route("/repsvm_agresores/<int:repsvm_agresor_id>")
def detail(repsvm_agresor_id):
    """Detalle de un Agresor"""
    repsvm_agresor = REPSVMAgresor.query.get_or_404(repsvm_agresor_id)
    return render_template("repsvm_agresores/detail.jinja2", repsvm_agresor=repsvm_agresor)
