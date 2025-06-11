"""
Ofi Plantillas, vistas
"""

import json
from flask import Blueprint, current_app, flash, redirect, render_template, request, url_for
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
    """DataTable JSON para listado de Ofi Plantillas"""
    # Tomar parámetros de Datatables
    draw, start, rows_per_page = get_datatable_parameters()
    # Consultar
    consulta = OfiPlantilla.query
    # Primero filtrar por columnas propias
    if "estatus" in request.form:
        consulta = consulta.filter_by(estatus=request.form["estatus"])
    else:
        consulta = consulta.filter_by(estatus="A")
    # Ordenar y paginar
    registros = consulta.order_by(OfiPlantilla.descripcion).offset(start).limit(rows_per_page).all()
    total = consulta.count()
    # Elaborar datos para DataTable
    data = []
    for resultado in registros:
        data.append(
            {
                "detalle": {
                    "descripcion": resultado.descripcion,
                    "url": url_for("ofi_plantillas.detail", ofi_plantilla_id=resultado.id),
                },
                "creado": resultado.creado.strftime("%Y-%m-%d %H:%M"),
                "esta_archivado": resultado.esta_archivado,
            }
        )
    # Entregar JSON
    return output_datatable_json(draw, total, data)


@ofi_plantillas.route("/ofi_plantillas")
def list_active():
    """Listado de Ofi Plantillas activos"""
    return render_template(
        "ofi_plantillas/list.jinja2",
        filtros=json.dumps({"estatus": "A"}),
        titulo="Plantillas",
        estatus="A",
    )


@ofi_plantillas.route("/ofi_plantillas/inactivos")
@permission_required(MODULO, Permiso.ADMINISTRAR)
def list_inactive():
    """Listado de Ofi Plantillas inactivos"""
    return render_template(
        "ofi_plantillas/list.jinja2",
        filtros=json.dumps({"estatus": "B"}),
        titulo="Plantillas inactivos",
        estatus="B",
    )


@ofi_plantillas.route("/ofi_plantillas/<int:ofi_plantilla_id>")
def detail(ofi_plantilla_id):
    """Detalle de un Ofi Plantilla"""
    ofi_plantilla = OfiPlantilla.query.get_or_404(ofi_plantilla_id)
    form = OfiPlantillaForm()
    form.descripcion.data = ofi_plantilla.descripcion
    form.contenido_sfdt.data = ofi_plantilla.contenido_sfdt
    form.esta_archivado.data = ofi_plantilla.esta_archivado
    return render_template(
        "ofi_plantillas/detail.jinja2",
        ofi_plantilla=ofi_plantilla,
        form=form,
        syncfusion_license_key=current_app.config["SYNCFUSION_LICENSE_KEY"],
    )


@ofi_plantillas.route("/ofi_plantillas/nuevo", methods=["GET", "POST"])
@permission_required(MODULO, Permiso.CREAR)
def new():
    """Nuevo Ofi Plantilla"""
    form = OfiPlantillaForm()
    if form.validate_on_submit():
        ofi_plantilla = OfiPlantilla(
            usuario=current_user,
            descripcion=safe_string(form.descripcion.data, save_enie=True),
            contenido_sfdt=form.contenido_sfdt.data,
        )
        ofi_plantilla.save()
        bitacora = Bitacora(
            modulo=Modulo.query.filter_by(nombre=MODULO).first(),
            usuario=current_user,
            descripcion=safe_message(f"Nuevo Ofi Plantilla {ofi_plantilla.descripcion}"),
            url=url_for("ofi_plantillas.detail", ofi_plantilla_id=ofi_plantilla.id),
        )
        bitacora.save()
        flash(bitacora.descripcion, "success")
        return redirect(bitacora.url)
    return render_template(
        "ofi_plantillas/new_syncfusion_document.jinja2",
        form=form,
        syncfusion_license_key=current_app.config["SYNCFUSION_LICENSE_KEY"],
    )


@ofi_plantillas.route("/ofi_plantillas/edicion/<int:ofi_plantilla_id>", methods=["GET", "POST"])
@permission_required(MODULO, Permiso.MODIFICAR)
def edit(ofi_plantilla_id):
    """Editar Ofi Plantilla"""
    ofi_plantilla = OfiPlantilla.query.get_or_404(ofi_plantilla_id)
    form = OfiPlantillaForm()
    if form.validate_on_submit():
        ofi_plantilla.descripcion = safe_string(form.descripcion.data, save_enie=True)
        ofi_plantilla.contenido_sfdt = form.contenido_sfdt.data
        ofi_plantilla.esta_archivado = form.esta_archivado.data
        ofi_plantilla.save()
        bitacora = Bitacora(
            modulo=Modulo.query.filter_by(nombre=MODULO).first(),
            usuario=current_user,
            descripcion=safe_message(f"Editado Ofi Plantilla {ofi_plantilla.descripcion}"),
            url=url_for("ofi_plantillas.detail", ofi_plantilla_id=ofi_plantilla.id),
        )
        bitacora.save()
        flash(bitacora.descripcion, "success")
        return redirect(bitacora.url)
    form.descripcion.data = ofi_plantilla.descripcion
    form.contenido_sfdt.data = ofi_plantilla.contenido_sfdt
    form.esta_archivado.data = ofi_plantilla.esta_archivado
    return render_template(
        "ofi_plantillas/edit_syncfusion_document.jinja2",
        form=form,
        ofi_plantilla=ofi_plantilla,
        syncfusion_license_key=current_app.config["SYNCFUSION_LICENSE_KEY"],
    )


@ofi_plantillas.route("/ofi_plantillas/eliminar/<int:ofi_plantilla_id>")
@permission_required(MODULO, Permiso.ADMINISTRAR)
def delete(ofi_plantilla_id):
    """Eliminar Ofi Plantilla"""
    ofi_plantilla = OfiPlantilla.query.get_or_404(ofi_plantilla_id)
    if ofi_plantilla.estatus == "A":
        ofi_plantilla.delete()
        bitacora = Bitacora(
            modulo=Modulo.query.filter_by(nombre=MODULO).first(),
            usuario=current_user,
            descripcion=safe_message(f"Eliminado Ofi Plantilla {ofi_plantilla.descripcion}"),
            url=url_for("ofi_plantillas.detail", ofi_plantilla_id=ofi_plantilla.id),
        )
        bitacora.save()
        flash(bitacora.descripcion, "success")
    return redirect(url_for("ofi_plantillas.detail", ofi_plantilla_id=ofi_plantilla.id))


@ofi_plantillas.route("/ofi_plantillas/recuperar/<int:ofi_plantilla_id>")
@permission_required(MODULO, Permiso.ADMINISTRAR)
def recover(ofi_plantilla_id):
    """Recuperar Ofi Plantilla"""
    ofi_plantilla = OfiPlantilla.query.get_or_404(ofi_plantilla_id)
    if ofi_plantilla.estatus == "B":
        ofi_plantilla.recover()
        bitacora = Bitacora(
            modulo=Modulo.query.filter_by(nombre=MODULO).first(),
            usuario=current_user,
            descripcion=safe_message(f"Recuperado Ofi Plantilla {ofi_plantilla.descripcion}"),
            url=url_for("ofi_plantillas.detail", ofi_plantilla_id=ofi_plantilla.id),
        )
        bitacora.save()
        flash(bitacora.descripcion, "success")
    return redirect(url_for("ofi_plantillas.detail", ofi_plantilla_id=ofi_plantilla.id))
