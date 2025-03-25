"""
Exh Exhortos Promociones Promoventes, vistas
"""

import json

from flask import Blueprint, flash, redirect, render_template, request, url_for
from flask_login import current_user, login_required
from sqlalchemy import or_

from hercules.blueprints.bitacoras.models import Bitacora
from hercules.blueprints.exh_exhortos_promociones.models import ExhExhortoPromocion
from hercules.blueprints.exh_exhortos_promociones_promoventes.forms import ExhExhortoPromocionPromoventeForm
from hercules.blueprints.exh_exhortos_promociones_promoventes.models import ExhExhortoPromocionPromovente
from hercules.blueprints.modulos.models import Modulo
from hercules.blueprints.permisos.models import Permiso
from hercules.blueprints.usuarios.decorators import permission_required
from lib.datatables import get_datatable_parameters, output_datatable_json
from lib.safe_string import safe_message, safe_string

MODULO = "EXH EXHORTOS PROMOCIONES PROMOVENTES"

exh_exhortos_promociones_promoventes = Blueprint("exh_exhortos_promociones_promoventes", __name__, template_folder="templates")


@exh_exhortos_promociones_promoventes.before_request
@login_required
@permission_required(MODULO, Permiso.VER)
def before_request():
    """Permiso por defecto"""


@exh_exhortos_promociones_promoventes.route("/exh_exhortos_promociones_promoventes/datatable_json", methods=["GET", "POST"])
def datatable_json():
    """DataTable JSON para listado de promoventes"""
    # Tomar parámetros de Datatables
    draw, start, rows_per_page = get_datatable_parameters()
    # Consultar
    consulta = ExhExhortoPromocionPromovente.query
    # Primero filtrar por columnas propias
    if "estatus" in request.form:
        consulta = consulta.filter_by(estatus=request.form["estatus"])
    else:
        consulta = consulta.filter_by(estatus="A")
    if "exh_exhorto_promocion_id" in request.form:
        consulta = consulta.filter_by(exh_exhorto_promocion_id=request.form["exh_exhorto_promocion_id"])
    # Ordenar y paginar
    registros = consulta.order_by(ExhExhortoPromocionPromovente.id.desc()).offset(start).limit(rows_per_page).all()
    total = consulta.count()
    # Elaborar datos para DataTable
    data = []
    for resultado in registros:
        data.append(
            {
                "detalle": {
                    "nombre": resultado.nombre_completo,
                    "url": url_for(
                        "exh_exhortos_promociones_promoventes.detail", exh_exhorto_promocion_promovente_id=resultado.id
                    ),
                },
                "genero_descripcion": resultado.genero_descripcion,
                "es_persona_moral": resultado.es_persona_moral,
                "tipo_parte_descripcion": resultado.tipo_parte_descripcion,
                "folio_origen_promocion": resultado.exh_exhorto_promocion.folio_origen_promocion,
            }
        )
    # Entregar JSON
    return output_datatable_json(draw, total, data)


@exh_exhortos_promociones_promoventes.route("/exh_exhortos_promociones_promoventes")
def list_active():
    """Listado de promoventes activos"""
    return render_template(
        "exh_exhortos_promociones_promoventes/list.jinja2",
        filtros=json.dumps({"estatus": "A"}),
        titulo="Exhortos Promociones Promoventes",
        estatus="A",
    )


@exh_exhortos_promociones_promoventes.route("/exh_exhortos_promociones_promoventes/inactivos")
@permission_required(MODULO, Permiso.ADMINISTRAR)
def list_inactive():
    """Listado de promoventes inactivos"""
    return render_template(
        "exh_exhortos_promociones_promoventes/list.jinja2",
        filtros=json.dumps({"estatus": "B"}),
        titulo="Exhortos Promociones Promoventes inactivos",
        estatus="B",
    )


@exh_exhortos_promociones_promoventes.route("/exh_exhortos_promociones_promoventes/<int:exh_exhorto_promocion_promovente_id>")
def detail(exh_exhorto_promocion_promovente_id):
    """Detalle de una parte"""
    exh_exhorto_promocion_promovente = ExhExhortoPromocionPromovente.query.get_or_404(exh_exhorto_promocion_promovente_id)
    return render_template(
        "exh_exhortos_promociones_promoventes/detail.jinja2", exh_exhorto_promocion_promovente=exh_exhorto_promocion_promovente
    )


@exh_exhortos_promociones_promoventes.route(
    "/exh_exhortos_promociones_promoventes/nuevo/<int:exh_exhorto_promocion_id>", methods=["GET", "POST"]
)
@permission_required(MODULO, Permiso.CREAR)
def new_with_exh_exhorto_promocion(exh_exhorto_promocion_id):
    """Nueva parte con el ID de una promoción"""
    exh_exhorto_promocion = ExhExhortoPromocion.query.get_or_404(exh_exhorto_promocion_id)
    form = ExhExhortoPromocionPromoventeForm()
    if form.validate_on_submit():
        # Si es persona moral no se necesitan los apellidos ni el genero
        es_persona_moral = True
        apellido_paterno = None
        apellido_materno = None
        genero = "-"
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
                    "exh_exhortos_promociones.detail",
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


@exh_exhortos_promociones_promoventes.route(
    "/exh_exhortos_promociones_promoventes/edicion/<int:exh_exhorto_promocion_promovente_id>", methods=["GET", "POST"]
)
@permission_required(MODULO, Permiso.MODIFICAR)
def edit(exh_exhorto_promocion_promovente_id):
    """Editar un promovente"""
    exh_exhorto_promocion_promovente = ExhExhortoPromocionPromovente.query.get_or_404(exh_exhorto_promocion_promovente_id)
    form = ExhExhortoPromocionPromoventeForm()
    if form.validate_on_submit():
        # Si es persona moral no se necesita definir apellidos o genero
        es_persona_moral = form.es_persona_moral.data
        if es_persona_moral == True:
            exh_exhorto_promocion_promovente.nombre = safe_string(form.nombre.data)
            exh_exhorto_promocion_promovente.apellido_paterno = None
            exh_exhorto_promocion_promovente.apellido_materno = None
        else:
            exh_exhorto_promocion_promovente.nombre = safe_string(form.nombre.data)
            exh_exhorto_promocion_promovente.apellido_paterno = safe_string(form.apellido_paterno.data)
            exh_exhorto_promocion_promovente.apellido_materno = safe_string(form.apellido_materno.data)
        exh_exhorto_promocion_promovente.es_persona_moral = es_persona_moral
        exh_exhorto_promocion_promovente.genero = safe_string(form.genero.data)
        # Si tipo_parte es NO DEFINIDO pedir un nombre para el tipo_parte_nombre
        pedir_tipo_parte_nombre = False
        tipo_parte_nombre = ""
        if form.tipo_parte.data == 0:
            pedir_tipo_parte_nombre = True
            tipo_parte_nombre = safe_string(form.tipo_parte_nombre.data)
        else:
            tipo_parte_nombre = None
        # Validación de campos necesarios
        if pedir_tipo_parte_nombre == True and tipo_parte_nombre == "":
            flash("Debe especificar un 'Tipo Parte Nombre'", "warning")
        else:
            exh_exhorto_promocion_promovente.tipo_parte = form.tipo_parte.data
            exh_exhorto_promocion_promovente.tipo_parte_nombre = tipo_parte_nombre
            exh_exhorto_promocion_promovente.save()
            bitacora = Bitacora(
                modulo=Modulo.query.filter_by(nombre=MODULO).first(),
                usuario=current_user,
                descripcion=safe_message(f"Editado Parte {exh_exhorto_promocion_promovente.nombre}"),
                url=url_for(
                    "exh_exhortos_promociones_promoventes.detail",
                    exh_exhorto_promocion_promovente_id=exh_exhorto_promocion_promovente.id,
                ),
            )
            bitacora.save()
            flash(bitacora.descripcion, "success")
            return redirect(bitacora.url)
    form.nombre.data = exh_exhorto_promocion_promovente.nombre
    form.apellido_paterno.data = exh_exhorto_promocion_promovente.apellido_paterno
    form.apellido_materno.data = exh_exhorto_promocion_promovente.apellido_materno
    form.es_persona_moral.data = exh_exhorto_promocion_promovente.es_persona_moral
    form.genero.data = exh_exhorto_promocion_promovente.genero
    form.tipo_parte.data = exh_exhorto_promocion_promovente.tipo_parte
    form.tipo_parte_nombre.data = exh_exhorto_promocion_promovente.tipo_parte_nombre
    return render_template(
        "exh_exhortos_promociones_promoventes/edit.jinja2",
        form=form,
        exh_exhorto_promocion_promovente=exh_exhorto_promocion_promovente,
    )


@exh_exhortos_promociones_promoventes.route(
    "/exh_exhortos_promociones_promoventes/eliminar/<int:exh_exhorto_promocion_promovente_id>"
)
@permission_required(MODULO, Permiso.ADMINISTRAR)
def delete(exh_exhorto_promocion_promovente_id):
    """Eliminar un promovente"""
    exh_exhorto_promocion_promovente = ExhExhortoPromocionPromovente.query.get_or_404(exh_exhorto_promocion_promovente_id)
    if exh_exhorto_promocion_promovente.estatus == "A":
        exh_exhorto_promocion_promovente.delete()
        bitacora = Bitacora(
            modulo=Modulo.query.filter_by(nombre=MODULO).first(),
            usuario=current_user,
            descripcion=safe_message(f"Eliminado Promovente {exh_exhorto_promocion_promovente.id}"),
            url=url_for(
                "exh_exhortos_promociones_promoventes.detail",
                exh_exhorto_promocion_promovente_id=exh_exhorto_promocion_promovente.id,
            ),
        )
        bitacora.save()
        flash(bitacora.descripcion, "success")
    return redirect(
        url_for(
            "exh_exhortos_promociones_promoventes.detail",
            exh_exhorto_promocion_promovente_id=exh_exhorto_promocion_promovente.id,
        )
    )


@exh_exhortos_promociones_promoventes.route(
    "/exh_exhortos_promociones_promoventes/recuperar/<int:exh_exhorto_promocion_promovente_id>"
)
@permission_required(MODULO, Permiso.ADMINISTRAR)
def recover(exh_exhorto_promocion_promovente_id):
    """Recuperar un promovente"""
    exh_exhorto_promocion_promovente = ExhExhortoPromocionPromovente.query.get_or_404(exh_exhorto_promocion_promovente_id)
    if exh_exhorto_promocion_promovente.estatus == "B":
        exh_exhorto_promocion_promovente.recover()
        bitacora = Bitacora(
            modulo=Modulo.query.filter_by(nombre=MODULO).first(),
            usuario=current_user,
            descripcion=safe_message(f"Recuperado Promovente {exh_exhorto_promocion_promovente.id}"),
            url=url_for(
                "exh_exhortos_promociones_promoventes.detail",
                exh_exhorto_promocion_promovente_id=exh_exhorto_promocion_promovente.id,
            ),
        )
        bitacora.save()
        flash(bitacora.descripcion, "success")
    return redirect(
        url_for(
            "exh_exhortos_promociones_promoventes.detail",
            exh_exhorto_promocion_promovente_id=exh_exhorto_promocion_promovente.id,
        )
    )
