"""
Web Unidades, vistas
"""

import json
from flask import Blueprint, flash, redirect, render_template, request, url_for
from flask_login import current_user, login_required

from lib.datatables import get_datatable_parameters, output_datatable_json
from lib.safe_string import safe_string, safe_message

from hercules.blueprints.bitacoras.models import Bitacora
from hercules.blueprints.modulos.models import Modulo
from hercules.blueprints.permisos.models import Permiso
from hercules.blueprints.usuarios.decorators import permission_required
from hercules.blueprints.web_unidades.models import WebUnidad

MODULO = "WEB UNIDADES"

web_unidades = Blueprint("web_unidades", __name__, template_folder="templates")


@web_unidades.before_request
@login_required
@permission_required(MODULO, Permiso.VER)
def before_request():
    """Permiso por defecto"""


@web_unidades.route("/web_unidades/<int:web_unidad_id>")
def detail(web_unidad_id):
    """Detalle de un Web Unidad"""
    return render_template("web_unidades/detail.jinja2", web_unidad_id=web_unidad_id)
