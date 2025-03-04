"""
Exh Exhortos Respuestas, vistas
"""

import json

from flask import Blueprint, flash, redirect, render_template, request, url_for
from flask_login import current_user, login_required

from hercules.blueprints.bitacoras.models import Bitacora
from hercules.blueprints.exh_exhortos_respuestas.models import ExhExhortoRespuesta
from hercules.blueprints.modulos.models import Modulo
from hercules.blueprints.permisos.models import Permiso
from hercules.blueprints.usuarios.decorators import permission_required
from lib.datatables import get_datatable_parameters, output_datatable_json
from lib.safe_string import safe_message, safe_string

MODULO = "EXH EXHORTOS RESPUESTAS"

exh_exhortos_respuestas = Blueprint("exh_exhortos_respuestas", __name__, template_folder="templates")


@exh_exhortos_respuestas.before_request
@login_required
@permission_required(MODULO, Permiso.VER)
def before_request():
    """Permiso por defecto"""


@exh_exhortos_respuestas.route("/exh_exhortos_respuestas/datatable_json", methods=["GET", "POST"])
def datatable_json():
    """DataTable JSON para listado de respuestas"""
    # Tomar parámetros de Datatables
    draw, start, rows_per_page = get_datatable_parameters()
    # Consultar
    consulta = ExhExhortoRespuesta.query
    # Primero filtrar por columnas propias
    if "estatus" in request.form:
        consulta = consulta.filter_by(estatus=request.form["estatus"])
    else:
        consulta = consulta.filter_by(estatus="A")
    if "exh_exhorto_id" in request.form:
        consulta = consulta.filter_by(exh_exhorto_id=request.form["exh_exhorto_id"])
    # Ordenar y paginar
    registros = consulta.order_by(ExhExhortoRespuesta.id).offset(start).limit(rows_per_page).all()
    total = consulta.count()
    # Elaborar datos para DataTable
    data = []
    for resultado in registros:
        data.append(
            {
                "detalle": {
                    "origen_id": resultado.origen_id,
                    "url": url_for("exh_exhortos_respuestas.detail", exh_exhorto_respuesta_id=resultado.id),
                },
                "fecha_hora_recepcion": resultado.fecha_origen.strftime("%Y-%m-%d %H:%M"),
                "remitente": resultado.remitente,
                "municipio_turnado_id": resultado.municipio_turnado_id,
                "area_turnado_id": resultado.area_turnado_id,
                "area_turnado_nombre": resultado.area_turnado_nombre,
                "numero_exhorto": resultado.numero_exhorto,
                "tipo_diligenciado": resultado.tipo_diligenciado,
                "estado": resultado.estado,
            }
        )
    # Entregar JSON
    return output_datatable_json(draw, total, data)


@exh_exhortos_respuestas.route("/exh_exhortos_respuestas")
def list_active():
    """Listado de respuestas activas"""
    return render_template(
        "exh_exhortos_respuestas/list.jinja2",
        filtros=json.dumps({"estatus": "A"}),
        titulo="Exhortos Respuestas",
        estatus="A",
    )


@exh_exhortos_respuestas.route("/exh_exhortos_respuestas/inactivos")
@permission_required(MODULO, Permiso.ADMINISTRAR)
def list_inactive():
    """Listado de respuestas inactivas"""
    return render_template(
        "exh_exhortos_respuestas/list.jinja2",
        filtros=json.dumps({"estatus": "B"}),
        titulo="Exhortos Respuestas inactivas",
        estatus="B",
    )


@exh_exhortos_respuestas.route("/exh_exhortos_respuestas/<int:exh_exhorto_respuesta_id>")
def detail(exh_exhorto_respuesta_id):
    """Detalle de un respuesta de exhorto"""
    exh_exhorto_respuesta = ExhExhortoRespuesta.query.get_or_404(exh_exhorto_respuesta_id)
    return render_template("exh_exhortos_respuestas/detail.jinja2", exh_exhorto_respuesta=exh_exhorto_respuesta)
