"""
Exh Exhortos Respuestas Archivos, vistas
"""

import json

from flask import Blueprint, flash, redirect, render_template, request, url_for
from flask_login import current_user, login_required

from hercules.blueprints.bitacoras.models import Bitacora
from hercules.blueprints.exh_exhortos_respuestas_archivos.models import ExhExhortoRespuestaArchivo
from hercules.blueprints.modulos.models import Modulo
from hercules.blueprints.permisos.models import Permiso
from hercules.blueprints.usuarios.decorators import permission_required
from lib.datatables import get_datatable_parameters, output_datatable_json
from lib.safe_string import safe_message, safe_string

MODULO = "EXH EXHORTOS RESPUESTAS ARCHIVOS"

exh_exhortos_respuestas_archivos = Blueprint("exh_exhortos_respuestas_archivos", __name__, template_folder="templates")


@exh_exhortos_respuestas_archivos.before_request
@login_required
@permission_required(MODULO, Permiso.VER)
def before_request():
    """Permiso por defecto"""


@exh_exhortos_respuestas_archivos.route("/exh_exhortos_respuestas_archivos/datatable_json", methods=["GET", "POST"])
def datatable_json():
    """DataTable JSON para listado de archivos de las respuestas"""
    # Tomar parámetros de Datatables
    draw, start, rows_per_page = get_datatable_parameters()
    # Consultar
    consulta = ExhExhortoRespuestaArchivo.query
    # Primero filtrar por columnas propias
    if "estatus" in request.form:
        consulta = consulta.filter_by(estatus=request.form["estatus"])
    else:
        consulta = consulta.filter_by(estatus="A")
    if "exh_exhorto_respuesta_id" in request.form:
        consulta = consulta.filter_by(exh_exhorto_respuesta_id=request.form["exh_exhorto_respuesta_id"])
    # Ordenar y paginar
    registros = consulta.order_by(ExhExhortoRespuestaArchivo.id).offset(start).limit(rows_per_page).all()
    total = consulta.count()
    # Elaborar datos para DataTable
    data = []
    for resultado in registros:
        data.append(
            {
                "detalle": {
                    "nombre_archivo": resultado.nombre_archivo,
                    "url": url_for("exh_exhortos_promociones_archivos.detail", exh_exhorto_promocion_archivo_id=resultado.id),
                },
                "descargar_pdf": {
                    "nombre_archivo": resultado.nombre_archivo,
                    "url": url_for(
                        "exh_exhortos_promociones_archivos.download_pdf", exh_exhorto_promocion_archivo_id=resultado.id
                    ),
                },
                "creado": resultado.creado.strftime("%Y-%m-%d %H:%M:%S"),
                "tipo_documento_nombre": resultado.tipo_documento_nombre,
                "estado": resultado.estado,
                "fecha_hora_recepcion": resultado.fecha_hora_recepcion.strftime("%Y-%m-%d %H:%M:%S"),
                "tamano": f"{round((resultado.tamano / 1024), 2)} MB",
            }
        )
    # Entregar JSON
    return output_datatable_json(draw, total, data)


@exh_exhortos_respuestas_archivos.route("/exh_exhortos_respuestas_archivos")
def list_active():
    """Listado de archivos de las respuestas activos"""
    return render_template(
        "exh_exhortos_respuestas_archivos/list.jinja2",
        filtros=json.dumps({"estatus": "A"}),
        titulo="Archivos de las respuestas",
        estatus="A",
    )


@exh_exhortos_respuestas_archivos.route("/exh_exhortos_respuestas_archivos/inactivos")
@permission_required(MODULO, Permiso.ADMINISTRAR)
def list_inactive():
    """Listado de archivos de las respuestas inactivos"""
    return render_template(
        "exh_exhortos_respuestas_archivos/list.jinja2",
        filtros=json.dumps({"estatus": "B"}),
        titulo="Archivos de las respuestas inactivos",
        estatus="B",
    )


@exh_exhortos_respuestas_archivos.route("/exh_exhortos_respuestas_archivos/<int:exh_exhorto_respuesta_archivo_id>")
def detail(exh_exhorto_respuesta_archivo_id):
    """Detalle de un archivo de respuesta"""
    exh_exhorto_respuesta_archivo_id = ExhExhortoRespuestaArchivo.query.get_or_404(exh_exhorto_respuesta_archivo_id)
    return render_template(
        "exh_exhortos_respuestas_archivos/detail.jinja2", exh_exhorto_respuesta_archivo_id=exh_exhorto_respuesta_archivo_id
    )
