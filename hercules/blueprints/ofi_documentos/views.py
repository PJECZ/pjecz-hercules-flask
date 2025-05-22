"""
Ofi Documentos, vistas
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
from hercules.blueprints.ofi_documentos.models import OfiDocumento

MODULO = "OFI DOCUMENTOS"

ofi_documentos = Blueprint('ofi_documentos', __name__, template_folder='templates')


@ofi_documentos.before_request
@login_required
@permission_required(MODULO, Permiso.VER)
def before_request():
    """ Permiso por defecto """
