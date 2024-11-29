"""
Exhortos Promociones Promoventes, vistas
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
from hercules.blueprints.exh_exhortos_promociones_promoventes.models import ExhExhortoPromocionPromovente
from hercules.blueprints.exh_exhortos_promociones.models import ExhExhortoPromocion
from hercules.blueprints.exh_exhortos_promociones_promoventes.forms import ExhExhortoPromocionPromoventeForm

MODULO = "EXH EXHORTOS PROMOCIONES PROMOVENTES"

exh_exhortos_promociones_promoventes = Blueprint("exh_exhortos_promociones_promoventes", __name__, template_folder="templates")


@exh_exhortos_promociones_promoventes.before_request
@login_required
@permission_required(MODULO, Permiso.VER)
def before_request():
    """Permiso por defecto"""


@exh_exhortos_promociones_promoventes.route("/exh_exhortos_promociones_promoventes/<int:exh_exhorto_promocion_promovente_id>")
def detail(exh_exhorto_promocion_promovente_id):
    """Detalle de un Parte"""
    exh_exhorto_promocion_promovente = ExhExhortoPromocionPromovente.query.get_or_404(exh_exhorto_promocion_promovente_id)
    return render_template(
        "exh_exhortos_promociones_promoventes/detail.jinja2", exh_exhorto_promocion_promovente=exh_exhorto_promocion_promovente
    )


@exh_exhortos_promociones_promoventes.route(
    "/exh_exhortos_promociones_promoventes/nuevo_con_exhorto_promocion/<int:exh_exhorto_promocion_id>", methods=["GET", "POST"]
)
@permission_required(MODULO, Permiso.CREAR)
def new_with_exh_exhorto_promocion(exh_exhorto_promocion_id):
    """Nueva Parte"""
    exh_exhorto_promocion = ExhExhortoPromocion.query.get_or_404(exh_exhorto_promocion_id)
    form = ExhExhortoPromocionPromoventeForm()
    if form.validate_on_submit():
        # Si es persona moral no se necesitan los apellidos ni el genero
        es_persona_moral = True
        apellido_paterno = None
        apellido_materno = None
        genero = "M"
        if form.es_persona_moral.data == False:
            es_persona_moral = False
            apellido_paterno = safe_string(form.apellido_paterno.data)
            apellido_materno = safe_string(form.apellido_materno.data)
            genero = safe_string(form.genero.data)
        # Si tipo_parte es NO DEFINIDO pedir un nombre para el tipo_parte_nombre
        pedir_tipo_parte_nombre = False
        tipo_parte_nombre = ""
        if form.tipo_parte.data == 0:
            pedir_tipo_parte_nombre = True
            tipo_parte_nombre = safe_string(form.tipo_parte_nombre.data)
        # Validación de campos necesarios
        if pedir_tipo_parte_nombre == True and tipo_parte_nombre == "":
            flash("Debe especificar un 'Tipo Parte Nombre'", "warning")
        else:
            exh_exhorto_promocion_promovente = ExhExhortoPromocionPromovente(
                exh_exhorto_promocion=exh_exhorto_promocion,
                es_persona_moral=es_persona_moral,
                nombre=safe_string(form.nombre.data),
                apellido_paterno=apellido_paterno,
                apellido_materno=apellido_materno,
                genero=genero,
                tipo_parte=form.tipo_parte.data,
                tipo_parte_nombre=tipo_parte_nombre,
            )
            exh_exhorto_promocion_promovente.save()
            bitacora = Bitacora(
                modulo=Modulo.query.filter_by(nombre=MODULO).first(),
                usuario=current_user,
                descripcion=safe_message(f"Nueva Parte {exh_exhorto_promocion_promovente.nombre}"),
                url=url_for(
                    "exh_exhortos_promocion.detail",
                    exh_exhorto_promocion_id=exh_exhorto_promocion_promovente.exh_exhorto_promocion.id,
                ),
            )
            bitacora.save()
            flash(bitacora.descripcion, "success")
            return redirect(bitacora.url)
    return render_template(
        "exh_exhortos_promociones_promoventes/new_with_exh_exhorto_promocion.jinja2",
        form=form,
        exh_exhorto_promocion=exh_exhorto_promocion,
    )
