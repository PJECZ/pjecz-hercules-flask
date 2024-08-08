"""
Web Paginas, vistas
"""

import json

from flask import Blueprint, flash, redirect, render_template, request, url_for
from flask_login import current_user, login_required

from hercules.blueprints.bitacoras.models import Bitacora
from hercules.blueprints.modulos.models import Modulo
from hercules.blueprints.permisos.models import Permiso
from hercules.blueprints.usuarios.decorators import permission_required
from hercules.blueprints.web_paginas.models import WebPagina
from lib.datatables import get_datatable_parameters, output_datatable_json
from lib.safe_string import safe_message, safe_string

MODULO = "WEB PAGINAS"

web_paginas = Blueprint("web_paginas", __name__, template_folder="templates")


@web_paginas.before_request
@login_required
@permission_required(MODULO, Permiso.VER)
def before_request():
    """Permiso por defecto"""


@web_paginas.route("/web_paginas")
def list_active():
    """Listado de WebPaginas activos"""
    return render_template(
        "web_paginas/list.jinja2",
        filtros=json.dumps({"estatus": "A"}),
        titulo="Paginas",
        estatus="A",
    )


@web_paginas.route("/web_paginas/inactivos")
@permission_required(MODULO, Permiso.ADMINISTRAR)
def list_inactive():
    """Listado de WebPaginas inactivas"""
    return render_template(
        "web_paginas/list.jinja2",
        filtros=json.dumps({"estatus": "B"}),
        titulo="Paginas inactivas",
        estatus="B",
    )


@web_paginas.route("/web_paginas/<int:web_pagina_id>")
def detail(web_pagina_id):
    """Detalle de una WebPagina"""
    web_pagina = WebPagina.query.get_or_404(web_pagina_id)
    return render_template("web_paginas/detail.jinja2", web_pagina=web_pagina)
