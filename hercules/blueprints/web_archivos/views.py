"""
Web Archivos, vistas
"""

import json

from flask import Blueprint, flash, redirect, render_template, request, url_for
from flask_login import current_user, login_required

from hercules.blueprints.bitacoras.models import Bitacora
from hercules.blueprints.modulos.models import Modulo
from hercules.blueprints.permisos.models import Permiso
from hercules.blueprints.usuarios.decorators import permission_required
from hercules.blueprints.web_archivos.models import WebArchivo
from lib.datatables import get_datatable_parameters, output_datatable_json
from lib.safe_string import safe_message, safe_string

MODULO = "WEB ARCHIVOS"

web_archivos = Blueprint("web_archivos", __name__, template_folder="templates")


@web_archivos.before_request
@login_required
@permission_required(MODULO, Permiso.VER)
def before_request():
    """Permiso por defecto"""


@web_archivos.route("/web_archivos")
def list_active():
    """Listado de WebArchivos activos"""
    return render_template(
        "web_archivos/list.jinja2",
        filtros=json.dumps({"estatus": "A"}),
        titulo="Archivos",
        estatus="A",
    )


@web_archivos.route("/web_archivos/inactivos")
@permission_required(MODULO, Permiso.ADMINISTRAR)
def list_inactive():
    """Listado de WebArchivos inactivos"""
    return render_template(
        "web_archivos/list.jinja2",
        filtros=json.dumps({"estatus": "B"}),
        titulo="Archivos inactivos",
        estatus="B",
    )


@web_archivos.route("/web_archivos/<int:web_archivo_id>")
def detail(web_archivo_id):
    """Detalle de un WebArchivo"""
    web_archivo = WebArchivo.query.get_or_404(web_archivo_id)
    return render_template("web_archivos/detail.jinja2", web_archivo=web_archivo)
