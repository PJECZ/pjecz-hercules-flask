"""
Ofi Plantillas, vistas
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
from hercules.blueprints.ofi_plantillas.models import OfiPlantilla
from hercules.blueprints.ofi_plantillas.forms import OfiPlantillaForm


MODULO = "OFI PLANTILLAS"

ofi_plantillas = Blueprint("ofi_plantillas", __name__, template_folder="templates")


@ofi_plantillas.before_request
@login_required
@permission_required(MODULO, Permiso.VER)
def before_request():
    """Permiso por defecto"""


@ofi_plantillas.route("/ofi_plantillas/datatable_json", methods=["GET", "POST"])
def datatable_json():
    """DataTable JSON para listado de Oficios-Plantillas"""
    # Tomar parámetros de Datatables
    draw, start, rows_per_page = get_datatable_parameters()
    # Consultar
    consulta = OfiPlantilla.query
    # Primero filtrar por columnas propias
    if "estatus" in request.form:
        consulta = consulta.filter_by(estatus=request.form["estatus"])
    else:
        consulta = consulta.filter_by(estatus="A")
    # if "persona_id" in request.form:
    #     consulta = consulta.filter_by(persona_id=request.form["persona_id"])
    # Luego filtrar por columnas de otras tablas
    # if "persona_rfc" in request.form:
    #     consulta = consulta.join(Persona)
    #     consulta = consulta.filter(Persona.rfc.contains(safe_rfc(request.form["persona_rfc"], search_fragment=True)))
    # Ordenar y paginar
    registros = consulta.order_by(OfiPlantilla.id).offset(start).limit(rows_per_page).all()
    total = consulta.count()
    # Elaborar datos para DataTable
    data = []
    for resultado in registros:
        data.append(
            {
                "detalle": {
                    "titulo": resultado.descripcion,
                    "url": url_for("ofi_plantillas.detail", ofi_plantilla_id=resultado.id),
                },
                "creado": resultado.creado.strftime("%Y-%m-%d %H:%M"),
            }
        )
    # Entregar JSON
    return output_datatable_json(draw, total, data)


@ofi_plantillas.route("/ofi_plantillas")
def list_active():
    """Listado de Oficios-Plantillas activos"""
    return render_template(
        "ofi_plantillas/list.jinja2",
        filtros=json.dumps({"estatus": "A"}),
        titulo="Oficios-Plantillas",
        estatus="A",
    )


@ofi_plantillas.route("/ofi_plantillas/inactivos")
@permission_required(MODULO, Permiso.ADMINISTRAR)
def list_inactive():
    """Listado de Oficios-Plantillas inactivos"""
    return render_template(
        "ofi_plantillas/list.jinja2",
        filtros=json.dumps({"estatus": "B"}),
        titulo="Oficios-Plantillas inactivos",
        estatus="B",
    )


@ofi_plantillas.route("/ofi_plantillas/<int:ofi_plantilla_id>")
def detail(ofi_plantilla_id):
    """Detalle de un Oficio-Plantilla"""
    ofi_plantilla = OfiPlantilla.query.get_or_404(ofi_plantilla_id)
    return render_template("ofi_plantillas/detail.jinja2", ofi_plantilla=ofi_plantilla)


@ofi_plantillas.route("/ofi_plantillas/nuevo", methods=["GET", "POST"])
@permission_required(MODULO, Permiso.CREAR)
def new():
    """Nuevo Oficio-Plantilla"""
    form = OfiPlantillaForm()
    if form.validate_on_submit():
        ofi_plantilla = OfiPlantilla(
            usuario=current_user,
            descripcion=safe_string(form.titulo.data, save_enie=True),
            contenido=safe_message(form.contenido.data),
        )
        ofi_plantilla.save()
        bitacora = Bitacora(
            modulo=Modulo.query.filter_by(nombre=MODULO).first(),
            usuario=current_user,
            descripcion=safe_message(f"Nuevo Oficio-Plantilla {ofi_plantilla.descripcion}"),
            url=url_for("ofi_plantillas.detail", ofi_plantilla_id=ofi_plantilla.id),
        )
        bitacora.save()
        flash(bitacora.descripcion, "success")
        return redirect(bitacora.url)
    return render_template("ofi_plantillas/new.jinja2", form=form)


@ofi_plantillas.route("/ofi_plantillas/edicion/<int:ofi_plantilla_id>", methods=["GET", "POST"])
@permission_required(MODULO, Permiso.MODIFICAR)
def edit(ofi_plantilla_id):
    """Editar Oficio-Plantilla"""
    ofi_plantilla = OfiPlantilla.query.get_or_404(ofi_plantilla_id)
    form = OfiPlantillaForm()
    if form.validate_on_submit():
        ofi_plantilla.descripcion = safe_string(form.titulo.data, save_enie=True)
        ofi_plantilla.contenido = safe_message(form.contenido.data)
        ofi_plantilla.save()
        bitacora = Bitacora(
            modulo=Modulo.query.filter_by(nombre=MODULO).first(),
            usuario=current_user,
            descripcion=safe_message(f"Editado Oficio-Plantilla {ofi_plantilla.descripcion}"),
            url=url_for("ofi_plantillas.detail", ofi_plantilla_id=ofi_plantilla.id),
        )
        bitacora.save()
        flash(bitacora.descripcion, "success")
        return redirect(bitacora.url)
    form.titulo.data = ofi_plantilla.descripcion
    form.contenido.data = ofi_plantilla.contenido
    return render_template("ofi_plantillas/edit.jinja2", form=form, ofi_plantilla=ofi_plantilla)


@ofi_plantillas.route("/ofi_plantillas/eliminar/<int:ofi_plantilla_id>")
@permission_required(MODULO, Permiso.ADMINISTRAR)
def delete(ofi_plantilla_id):
    """Eliminar Oficio-Plantilla"""
    ofi_plantilla = OfiPlantilla.query.get_or_404(ofi_plantilla_id)
    if ofi_plantilla.estatus == "A":
        ofi_plantilla.delete()
        bitacora = Bitacora(
            modulo=Modulo.query.filter_by(nombre=MODULO).first(),
            usuario=current_user,
            descripcion=safe_message(f"Eliminado Oficio-Plantilla {ofi_plantilla.descripcion}"),
            url=url_for("ofi_plantillas.detail", ofi_plantilla_id=ofi_plantilla.id),
        )
        bitacora.save()
        flash(bitacora.descripcion, "success")
    return redirect(url_for("ofi_plantillas.detail", ofi_plantilla_id=ofi_plantilla.id))


@ofi_plantillas.route("/ofi_plantillas/recuperar/<int:ofi_plantilla_id>")
@permission_required(MODULO, Permiso.ADMINISTRAR)
def recover(ofi_plantilla_id):
    """Recuperar Oficio-Plantilla"""
    ofi_plantilla = OfiPlantilla.query.get_or_404(ofi_plantilla_id)
    if ofi_plantilla.estatus == "B":
        ofi_plantilla.recover()
        bitacora = Bitacora(
            modulo=Modulo.query.filter_by(nombre=MODULO).first(),
            usuario=current_user,
            descripcion=safe_message(f"Recuperado Oficio-Plantilla {ofi_plantilla.descripcion}"),
            url=url_for("ofi_plantillas.detail", ofi_plantilla_id=ofi_plantilla.id),
        )
        bitacora.save()
        flash(bitacora.descripcion, "success")
    return redirect(url_for("ofi_plantillas.detail", ofi_plantilla_id=ofi_plantilla.id))
