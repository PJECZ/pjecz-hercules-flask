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
from hercules.blueprints.ofi_documentos.forms import OfiDocumentoForm


MODULO = "OFI DOCUMENTOS"

ofi_documentos = Blueprint("ofi_documentos", __name__, template_folder="templates")


@ofi_documentos.before_request
@login_required
@permission_required(MODULO, Permiso.VER)
def before_request():
    """Permiso por defecto"""


@ofi_documentos.route("/ofi_documentos/datatable_json", methods=["GET", "POST"])
def datatable_json():
    """DataTable JSON para listado de Ofi-Documentos"""
    # Tomar parámetros de Datatables
    draw, start, rows_per_page = get_datatable_parameters()
    # Consultar
    consulta = OfiDocumento.query
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
    registros = consulta.order_by(OfiDocumento.id).offset(start).limit(rows_per_page).all()
    total = consulta.count()
    # Elaborar datos para DataTable
    data = []
    for resultado in registros:
        data.append(
            {
                "detalle": {
                    "id": resultado.id,
                    "url": url_for("ofi_documentos.detail", ofi_documento_id=resultado.id),
                },
                "folio": resultado.folio,
                "titulo": resultado.descripcion,
                "creado": resultado.creado.strftime("%Y-%m-%d %H:%M"),
                "estado": resultado.estado,
            }
        )
    # Entregar JSON
    return output_datatable_json(draw, total, data)


@ofi_documentos.route("/ofi_documentos")
def list_active():
    """Listado de Ofi-Documentos activos"""
    return render_template(
        "ofi_documentos/list.jinja2",
        filtros=json.dumps({"estatus": "A"}),
        titulo="Oficios",
        estatus="A",
    )


@ofi_documentos.route("/ofi_documentos/inactivos")
@permission_required(MODULO, Permiso.ADMINISTRAR)
def list_inactive():
    """Listado de Ofi-Documentos inactivos"""
    return render_template(
        "ofi_documentos/list.jinja2",
        filtros=json.dumps({"estatus": "B"}),
        titulo="Oficios inactivos",
        estatus="B",
    )


@ofi_documentos.route("/ofi_documentos/<int:ofi_documento_id>")
def detail(ofi_documento_id):
    """Detalle de un Ofi-Documento"""
    ofi_documento = OfiDocumento.query.get_or_404(ofi_documento_id)
    return render_template("ofi_documentos/detail.jinja2", ofi_documento=ofi_documento)


@ofi_documentos.route("/ofi_documentos/nuevo", methods=["GET", "POST"])
@permission_required(MODULO, Permiso.CREAR)
def new():
    """Nuevo Ofi-Documento"""
    form = OfiDocumentoForm()
    if form.validate_on_submit():
        ofi_documento = OfiDocumento(
            usuario=current_user,
            folio=form.folio.data,
            descripcion=safe_string(form.titulo.data, save_enie=True),
            contenido=safe_message(form.contenido.data),
            estado="BORRADOR",
            es_archivado=False,
            firma_simple="",
        )
        ofi_documento.save()
        bitacora = Bitacora(
            modulo=Modulo.query.filter_by(nombre=MODULO).first(),
            usuario=current_user,
            descripcion=safe_message(f"Nuevo Oficio-Documento {ofi_documento.id}"),
            url=url_for("ofi_documentos.detail", ofi_documento_id=ofi_documento.id),
        )
        bitacora.save()
        flash(bitacora.descripcion, "success")
        return redirect(bitacora.url)
    return render_template("ofi_documentos/new.jinja2", form=form)


@ofi_documentos.route("/ofi_documentos/edicion/<int:ofi_documento_id>", methods=["GET", "POST"])
@permission_required(MODULO, Permiso.MODIFICAR)
def edit(ofi_documento_id):
    """Editar Oficio-Documento"""
    ofi_documento = OfiDocumento.query.get_or_404(ofi_documento_id)
    form = OfiDocumentoForm()
    if form.validate_on_submit():
        ofi_documento.descripcion = safe_string(form.titulo.data, save_enie=True)
        ofi_documento.folio = form.folio.data
        ofi_documento.contenido = safe_message(form.contenido.data)
        ofi_documento.save()
        bitacora = Bitacora(
            modulo=Modulo.query.filter_by(nombre=MODULO).first(),
            usuario=current_user,
            descripcion=safe_message(f"Editado Oficio-Documento {ofi_documento.descripcion}"),
            url=url_for("ofi_documentos.detail", ofi_documento_id=ofi_documento.id),
        )
        bitacora.save()
        flash(bitacora.descripcion, "success")
        return redirect(bitacora.url)
    form.titulo.data = ofi_documento.descripcion
    form.folio.data = ofi_documento.folio
    form.contenido.data = ofi_documento.contenido
    return render_template("ofi_documentos/edit.jinja2", form=form, ofi_documento=ofi_documento)


@ofi_documentos.route("/ofi_documentos/eliminar/<int:ofi_documento_id>")
@permission_required(MODULO, Permiso.ADMINISTRAR)
def delete(ofi_documento_id):
    """Eliminar Ofi-Documento"""
    ofi_documento = OfiDocumento.query.get_or_404(ofi_documento_id)
    if ofi_documento.estatus == "A":
        ofi_documento.delete()
        bitacora = Bitacora(
            modulo=Modulo.query.filter_by(nombre=MODULO).first(),
            usuario=current_user,
            descripcion=safe_message(f"Eliminado Ofi-Documento {ofi_documento.id}"),
            url=url_for("ofi_documentos.detail", ofi_documento_id=ofi_documento.id),
        )
        bitacora.save()
        flash(bitacora.descripcion, "success")
    return redirect(url_for("ofi_documentos.detail", ofi_documento_id=ofi_documento.id))


@ofi_documentos.route("/ofi_documentos/recuperar/<int:ofi_documento_id>")
@permission_required(MODULO, Permiso.ADMINISTRAR)
def recover(ofi_documento_id):
    """Recuperar Ofi-Documento"""
    ofi_documento = OfiDocumento.query.get_or_404(ofi_documento_id)
    if ofi_documento.estatus == "B":
        ofi_documento.recover()
        bitacora = Bitacora(
            modulo=Modulo.query.filter_by(nombre=MODULO).first(),
            usuario=current_user,
            descripcion=safe_message(f"Recuperado Ofi-Documento {ofi_documento.id}"),
            url=url_for("ofi_documentos.detail", ofi_documento_id=ofi_documento.id),
        )
        bitacora.save()
        flash(bitacora.descripcion, "success")
    return redirect(url_for("ofi_documentos.detail", ofi_documento_id=ofi_documento.id))
