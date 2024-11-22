"""
Exhorto - Actualizaciones, vistas
"""

import json
from datetime import datetime
from flask import Blueprint, flash, redirect, render_template, request, url_for
from flask_login import current_user, login_required

from lib.datatables import get_datatable_parameters, output_datatable_json
from lib.safe_string import safe_string, safe_message

from hercules.blueprints.bitacoras.models import Bitacora
from hercules.blueprints.modulos.models import Modulo
from hercules.blueprints.permisos.models import Permiso
from hercules.blueprints.usuarios.decorators import permission_required
from hercules.blueprints.exh_exhortos_actualizaciones.models import ExhExhortoActualizacion
from hercules.blueprints.exh_exhortos_actualizaciones.forms import ExhExhortoActualizacionNewForm
from hercules.blueprints.exh_exhortos.models import ExhExhorto

MODULO = "EXH EXHORTOS ACTUALIZACIONES"

exh_exhortos_actualizaciones = Blueprint("exh_exhortos_actualizaciones", __name__, template_folder="templates")


@exh_exhortos_actualizaciones.before_request
@login_required
@permission_required(MODULO, Permiso.VER)
def before_request():
    """Permiso por defecto"""


@exh_exhortos_actualizaciones.route("/exh_exhortos_actualizaciones/<int:exh_exhorto_actualizacion>")
def detail(exh_exhorto_actualizacion):
    """Detalle de un Actualización"""
    exh_exhorto_actualizacion = ExhExhortoActualizacion.query.get_or_404(exh_exhorto_actualizacion)
    return render_template("exh_exhortos_actualizaciones/detail.jinja2", exh_exhorto_actualizacion=exh_exhorto_actualizacion)


@exh_exhortos_actualizaciones.route("/exh_exhortos_actualizaciones/nuevo/<int:exh_exhorto_id>", methods=["GET", "POST"])
@permission_required(MODULO, Permiso.CREAR)
def new_with_exh_exhorto(exh_exhorto_id):
    """Nuevo Actualización"""
    exh_exhorto = ExhExhorto.query.get_or_404(exh_exhorto_id)
    form = ExhExhortoActualizacionNewForm()
    if form.validate_on_submit():
        exh_exhorto_actualizacion = ExhExhortoActualizacion(
            exh_exhorto=exh_exhorto,
            actualizacion_origen_id=safe_string(form.origen_id.data),
            tipo_actualizacion=safe_string(form.tipo_actualizacion.data),
            descripcion=safe_string(form.descripcion.data),
            fecha_hora=datetime.now(),
        )
        exh_exhorto_actualizacion.save()
        bitacora = Bitacora(
            modulo=Modulo.query.filter_by(nombre=MODULO).first(),
            usuario=current_user,
            descripcion=safe_message(f"Nuevo Actualización {exh_exhorto_actualizacion.id}"),
            url=url_for("exh_exhortos_actualizaciones.detail", exh_exhorto_actualizacion_id=exh_exhorto_actualizacion.id),
        )
        bitacora.save()
        flash(bitacora.descripcion, "success")
        return redirect(bitacora.url)
    return render_template("exh_exhortos_actualizaciones/new_with_exh_exhorto.jinja2", form=form, exh_exhorto=exh_exhorto)
