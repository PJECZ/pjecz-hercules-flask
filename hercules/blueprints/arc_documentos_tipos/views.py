"""
Archivo - Documentos Tipos, vistas
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
from hercules.blueprints.arc_documentos_tipos.models import ArcDocumentoTipo
from hercules.blueprints.arc_documentos_tipos.forms import ArcDocumentoTipoForm

MODULO = "ARC DOCUMENTOS TIPOS"

arc_documentos_tipos = Blueprint("arc_documentos_tipos", __name__, template_folder="templates")


@arc_documentos_tipos.before_request
@login_required
@permission_required(MODULO, Permiso.VER)
def before_request():
    """Permiso por defecto"""


@arc_documentos_tipos.route("/arc_documentos_tipos/datatable_json", methods=["GET", "POST"])
def datatable_json():
    """DataTable JSON para listado de Arc Documentos Tipos"""
    # Tomar parámetros de Datatables
    draw, start, rows_per_page = get_datatable_parameters()
    # Consultar
    consulta = ArcDocumentoTipo.query
    # Primero filtrar por columnas propias
    if "estatus" in request.form:
        consulta = consulta.filter_by(estatus=request.form["estatus"])
    else:
        consulta = consulta.filter_by(estatus="A")
    if "nombre" in request.form:
        nombre = safe_string(request.form["nombre"], save_enie=True)
        if nombre != "":
            consulta = consulta.filter(ArcDocumentoTipo.nombre.contains(nombre))
    # Luego filtrar por columnas de otras tablas
    # if "persona_rfc" in request.form:
    #     consulta = consulta.join(Persona)
    #     consulta = consulta.filter(Persona.rfc.contains(safe_rfc(request.form["persona_rfc"], search_fragment=True)))
    # Ordenar y paginar
    registros = consulta.order_by(ArcDocumentoTipo.nombre).offset(start).limit(rows_per_page).all()
    total = consulta.count()
    # Elaborar datos para DataTable
    data = []
    for resultado in registros:
        data.append(
            {
                "detalle": {
                    "nombre": resultado.nombre,
                    "url": url_for("arc_documentos_tipos.detail", arc_documento_tipo_id=resultado.id),
                },
            }
        )
    # Entregar JSON
    return output_datatable_json(draw, total, data)


@arc_documentos_tipos.route("/arc_documentos_tipos")
def list_active():
    """Listado de Tipos Documentos activos"""
    return render_template(
        "arc_documentos_tipos/list.jinja2",
        filtros=json.dumps({"estatus": "A"}),
        titulo="Archivo - Tipos Documentos",
        estatus="A",
    )


@arc_documentos_tipos.route("/arc_documentos_tipos/inactivos")
@permission_required(MODULO, Permiso.ADMINISTRAR)
def list_inactive():
    """Listado de Tipos Documentos inactivos"""
    return render_template(
        "arc_documentos_tipos/list.jinja2",
        filtros=json.dumps({"estatus": "B"}),
        titulo="Archivo - Tipos Documentos inactivos",
        estatus="B",
    )


@arc_documentos_tipos.route("/arc_documentos_tipos/<int:arc_documento_tipo_id>")
def detail(arc_documento_tipo_id):
    """Detalle de un Archivo - Tipo Documento"""
    arc_documento_tipo = ArcDocumentoTipo.query.get_or_404(arc_documento_tipo_id)
    return render_template("arc_documentos_tipos/detail.jinja2", arc_documento_tipo=arc_documento_tipo)


@arc_documentos_tipos.route("/arc_documentos_tipos/nuevo", methods=["GET", "POST"])
@permission_required(MODULO, Permiso.CREAR)
def new():
    """Nuevo Archivo - Tipo de Documento"""
    form = ArcDocumentoTipoForm()
    if form.validate_on_submit():
        # Validar nombre repetido
        nombre = safe_string(form.nombre.data, save_enie=True)
        tipo_existente = ArcDocumentoTipo.query.filter_by(nombre=nombre).first()
        if tipo_existente:
            flash(f"Este nombre '{nombre}' ya existe, debe ser único.", "warning")
            return render_template("arc_documentos_tipos/new.jinja2", form=form)
        arc_documento_tipo = ArcDocumentoTipo(nombre=nombre)
        arc_documento_tipo.save()
        bitacora = Bitacora(
            modulo=Modulo.query.filter_by(nombre=MODULO).first(),
            usuario=current_user,
            descripcion=safe_message(f"Nuevo Archivo - Tipo de Documento {arc_documento_tipo.nombre}"),
            url=url_for("arc_documentos_tipos.detail", arc_documento_tipo_id=arc_documento_tipo.id),
        )
        bitacora.save()
        flash(bitacora.descripcion, "success")
        return redirect(bitacora.url)
    return render_template("arc_documentos_tipos/new.jinja2", form=form)


@arc_documentos_tipos.route("/arc_documentos_tipos/edicion/<int:arc_documento_tipo_id>", methods=["GET", "POST"])
@permission_required(MODULO, Permiso.MODIFICAR)
def edit(arc_documento_tipo_id):
    """Editar Archivo - Tipo Documento"""
    arc_documento_tipo = ArcDocumentoTipo.query.get_or_404(arc_documento_tipo_id)
    form = ArcDocumentoTipoForm()
    if form.validate_on_submit():
        # Validar que no exista otro con el mismo nombre
        nombre = safe_string(form.nombre.data, save_enie=True)
        tipo_existente = ArcDocumentoTipo.query.filter_by(nombre=nombre).first()
        if tipo_existente:
            flash(f"Este nombre '{nombre}' ya existe, debe ser único.", "warning")
            return redirect(url_for("arc_documentos_tipos.edit", arc_documento_tipo_id=arc_documento_tipo_id))
        # Guardar cambios
        arc_documento_tipo.nombre = nombre
        arc_documento_tipo.save()
        bitacora = Bitacora(
            modulo=Modulo.query.filter_by(nombre=MODULO).first(),
            usuario=current_user,
            descripcion=safe_message(f"Editado Archivo - Tipo Documento {arc_documento_tipo.nombre}"),
            url=url_for("arc_documentos_tipos.detail", arc_documento_tipo_id=arc_documento_tipo.id),
        )
        bitacora.save()
        flash(bitacora.descripcion, "success")
        return redirect(bitacora.url)
    form.nombre.data = arc_documento_tipo.nombre
    return render_template("arc_documentos_tipos/edit.jinja2", form=form, arc_documento_tipo=arc_documento_tipo)


@arc_documentos_tipos.route("/arc_documentos_tipos/eliminar/<int:arc_documento_tipo_id>")
@permission_required(MODULO, Permiso.ADMINISTRAR)
def delete(arc_documento_tipo_id):
    """Eliminar Archivo - Tipo de Documento"""
    arc_documento_tipo = ArcDocumentoTipo.query.get_or_404(arc_documento_tipo_id)
    if arc_documento_tipo.estatus == "A":
        arc_documento_tipo.delete()
        bitacora = Bitacora(
            modulo=Modulo.query.filter_by(nombre=MODULO).first(),
            usuario=current_user,
            descripcion=safe_message(f"Eliminado Archivo - Tipo de Documento {arc_documento_tipo.nombre}"),
            url=url_for("arc_documentos_tipos.detail", arc_documento_tipo_id=arc_documento_tipo.id),
        )
        bitacora.save()
        flash(bitacora.descripcion, "success")
    return redirect(url_for("arc_documentos_tipos.detail", arc_documento_tipo_id=arc_documento_tipo.id))


@arc_documentos_tipos.route("/arc_documentos_tipos/recuperar/<int:arc_documento_tipo_id>")
@permission_required(MODULO, Permiso.ADMINISTRAR)
def recover(arc_documento_tipo_id):
    """Recuperar Archivo - Tipo de Documento"""
    arc_documento_tipo = ArcDocumentoTipo.query.get_or_404(arc_documento_tipo_id)
    if arc_documento_tipo.estatus == "B":
        arc_documento_tipo.recover()
        bitacora = Bitacora(
            modulo=Modulo.query.filter_by(nombre=MODULO).first(),
            usuario=current_user,
            descripcion=safe_message(f"Recuperado Archivo - Tipo de Documento {arc_documento_tipo.nombre}"),
            url=url_for("arc_documentos_tipos.detail", arc_documento_tipo_id=arc_documento_tipo.id),
        )
        bitacora.save()
        flash(bitacora.descripcion, "success")
    return redirect(url_for("arc_documentos_tipos.detail", arc_documento_tipo_id=arc_documento_tipo.id))


@arc_documentos_tipos.route("/arc_documentos_tipos/tipos_documentos_json", methods=["POST"])
def query_tipos_documentos_json():
    """Proporcionar el JSON de los tipos de documentos con un Select2"""
    consulta = ArcDocumentoTipo.query.filter_by(estatus="A")
    if "nombre" in request.form:
        nombre = safe_string(request.form["nombre"])
        consulta = consulta.filter(ArcDocumentoTipo.nombre.contains(nombre))
    results = []
    for tipo in consulta.order_by(ArcDocumentoTipo.nombre).limit(15).all():
        results.append({"id": tipo.id, "text": tipo.nombre})
    return {"results": results, "pagination": {"more": False}}
