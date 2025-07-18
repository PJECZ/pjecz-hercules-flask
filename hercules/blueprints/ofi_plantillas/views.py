"""
Ofi Plantillas, vistas
"""

import json
from flask import Blueprint, current_app, flash, redirect, render_template, request, url_for
from flask_login import current_user, login_required
from sqlalchemy import String, cast


from lib.datatables import get_datatable_parameters, output_datatable_json
from lib.safe_string import safe_string, safe_message, safe_uuid, safe_clave

from hercules.blueprints.bitacoras.models import Bitacora
from hercules.blueprints.modulos.models import Modulo
from hercules.blueprints.permisos.models import Permiso
from hercules.blueprints.usuarios.decorators import permission_required
from hercules.blueprints.ofi_plantillas.models import OfiPlantilla
from hercules.blueprints.ofi_plantillas.forms import OfiPlantillaForm
from hercules.blueprints.usuarios.models import Usuario
from hercules.blueprints.autoridades.models import Autoridad


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
        consulta = consulta.filter(OfiPlantilla.estatus == request.form["estatus"])
    else:
        consulta = consulta.filter(OfiPlantilla.estatus == "A")
    if "id" in request.form:
        id = safe_string(request.form["id"])
        if id:
            consulta = consulta.filter(cast(OfiPlantilla.id, String).contains(id.lower()))
    if "descripcion" in request.form:
        descripcion = safe_string(request.form["descripcion"], save_enie=True)
        if descripcion:
            consulta = consulta.filter(OfiPlantilla.descripcion.contains(descripcion))
    # Luego filtrar por columnas de otras tablas
    tabla_usuario_incluida = False
    if "propietario" in request.form:
        if tabla_usuario_incluida is False:
            consulta = consulta.join(Usuario)
            tabla_usuario_incluida = True
        propietario = request.form["propietario"].lower()
        consulta = consulta.filter(Usuario.email.contains(propietario))
    if "autoridad" in request.form:
        autoridad = safe_clave(request.form["autoridad"])
        if autoridad:
            if tabla_usuario_incluida is False:
                consulta = consulta.join(Usuario)
                tabla_usuario_incluida = True
            consulta = consulta.join(Autoridad, Usuario.autoridad_id == Autoridad.id)
            consulta = consulta.filter(Autoridad.clave.contains(autoridad))
    if "usuario_autoridad_id" in request.form:
        if tabla_usuario_incluida is False:
            consulta = consulta.join(Usuario)
            tabla_usuario_incluida = True
        consulta = consulta.filter(Usuario.autoridad_id == request.form["usuario_autoridad_id"])
    # Ordenar y paginar
    registros = consulta.order_by(OfiPlantilla.descripcion).offset(start).limit(rows_per_page).all()
    total = consulta.count()
    # Elaborar datos para DataTable
    data = []
    for resultado in registros:
        data.append(
            {
                "detalle": {
                    "id": resultado.id,
                    "url": url_for("ofi_plantillas.detail", ofi_plantilla_id=resultado.id),
                    "url_nuevo": url_for("ofi_documentos.new", ofi_plantilla_id=resultado.id),
                },
                "propietario": {
                    "email": resultado.usuario.email,
                    "nombre": resultado.usuario.nombre,
                    "url": url_for("usuarios.detail", usuario_id=resultado.usuario.id),
                },
                "autoridad": {
                    "clave": resultado.usuario.autoridad.clave,
                    "nombre": resultado.usuario.autoridad.descripcion_corta,
                    "url": (
                        url_for("autoridades.detail", autoridad_id=resultado.usuario.autoridad.id)
                        if current_user.can_view("AUTORIDADES")
                        else ""
                    ),
                    "color_renglon": (
                        resultado.usuario.autoridad.tabla_renglon_color
                        if resultado.usuario.autoridad.tabla_renglon_color
                        else ""
                    ),
                },
                "descripcion": resultado.descripcion,
                "creado": resultado.creado.strftime("%Y-%m-%d %H:%M"),
                "esta_archivado": resultado.esta_archivado,
            }
        )
    # Entregar JSON
    return output_datatable_json(draw, total, data)


@ofi_plantillas.route("/ofi_plantillas")
def list_active():
    """Listado de Ofi Plantillas activos"""
    if current_user.can_admin(MODULO):
        return render_template(
            "ofi_plantillas/list_admin.jinja2",
            filtros=json.dumps({"estatus": "A"}),
            titulo="Plantillas",
            estatus="A",
        )
    return render_template(
        "ofi_plantillas/list.jinja2",
        filtros=json.dumps({"estatus": "A", "usuario_autoridad_id": current_user.autoridad.id}),
        titulo="Plantillas",
        estatus="A",
    )


@ofi_plantillas.route("/ofi_plantillas/inactivos")
@permission_required(MODULO, Permiso.ADMINISTRAR)
def list_inactive():
    """Listado de Ofi Plantillas inactivos"""
    if current_user.can_admin(MODULO):
        return render_template(
            "ofi_plantillas/list_admin.jinja2",
            filtros=json.dumps({"estatus": "B"}),
            titulo="Plantillas inactivos",
            estatus="B",
        )
    return render_template(
        "ofi_plantillas/list.jinja2",
        filtros=json.dumps({"estatus": "B", "usuario_autoridad_id": current_user.autoridad.id}),
        titulo="Plantillas inactivos",
        estatus="B",
    )


@ofi_plantillas.route("/ofi_plantillas/<ofi_plantilla_id>")
def detail(ofi_plantilla_id):
    """Detalle de un Ofi Plantilla"""
    ofi_plantilla_id = safe_uuid(ofi_plantilla_id)
    if not ofi_plantilla_id:
        flash("ID de plantilla inválido", "warning")
        return redirect(url_for("ofi_plantillas.list_active"))
    ofi_plantilla = OfiPlantilla.query.get_or_404(ofi_plantilla_id)
    form = OfiPlantillaForm()
    form.descripcion.data = ofi_plantilla.descripcion
    form.contenido_sfdt.data = ofi_plantilla.contenido_sfdt
    form.esta_archivado.data = ofi_plantilla.esta_archivado
    # Entregar el detalle
    return render_template(
        "ofi_plantillas/detail.jinja2",
        ofi_plantilla=ofi_plantilla,
        form=form,
    )


@ofi_plantillas.route("/ofi_plantillas/nuevo", methods=["GET", "POST"])
@permission_required(MODULO, Permiso.CREAR)
def new():
    """Nuevo Ofi Plantilla"""
    form = OfiPlantillaForm()
    if form.validate_on_submit():
        # Validar propietario
        propietario = Usuario.query.filter_by(id=form.propietario.data).first()
        if not propietario:
            flash("Propietario inválido", "warning")
            return redirect(url_for("ofi_plantillas.new"))
        ofi_plantilla = OfiPlantilla(
            usuario=propietario,
            descripcion=safe_string(form.descripcion.data, save_enie=True),
            contenido_md=form.contenido_md.data,
            contenido_html=form.contenido_html.data,
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
    # Entregar el formulario
    return render_template(
        "ofi_plantillas/new_ckeditor5.jinja2",
        form=form,
    )


@ofi_plantillas.route("/ofi_plantillas/edicion/<ofi_plantilla_id>", methods=["GET", "POST"])
@permission_required(MODULO, Permiso.MODIFICAR)
def edit(ofi_plantilla_id):
    """Editar Ofi Plantilla"""
    ofi_plantilla_id = safe_uuid(ofi_plantilla_id)
    if not ofi_plantilla_id:
        flash("ID de plantilla inválido", "warning")
        return redirect(url_for("ofi_plantillas.list_active"))
    ofi_plantilla = OfiPlantilla.query.get_or_404(ofi_plantilla_id)
    form = OfiPlantillaForm()
    if form.validate_on_submit():
        # Validar propietario
        es_valido = True
        propietario = Usuario.query.filter_by(id=form.propietario.data).first()
        if not propietario:
            flash("Propietario inválido", "warning")
            es_valido = False
        if es_valido:
            ofi_plantilla.descripcion = safe_string(form.descripcion.data, save_enie=True)
            ofi_plantilla.usuario = propietario
            ofi_plantilla.contenido_md = form.contenido_md.data
            ofi_plantilla.contenido_html = form.contenido_html.data
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
    form.contenido_md.data = ofi_plantilla.contenido_md
    form.contenido_html.data = ofi_plantilla.contenido_html
    form.contenido_sfdt.data = ofi_plantilla.contenido_sfdt
    form.esta_archivado.data = ofi_plantilla.esta_archivado
    # Entregar el formulario
    return render_template(
        "ofi_plantillas/edit_ckeditor5.jinja2",
        form=form,
        ofi_plantilla=ofi_plantilla,
    )


@ofi_plantillas.route("/ofi_plantillas/eliminar/<ofi_plantilla_id>")
@permission_required(MODULO, Permiso.ADMINISTRAR)
def delete(ofi_plantilla_id):
    """Eliminar Ofi Plantilla"""
    ofi_plantilla_id = safe_uuid(ofi_plantilla_id)
    if not ofi_plantilla_id:
        flash("ID de plantilla inválido", "warning")
        return redirect(url_for("ofi_plantillas.list_active"))
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


@ofi_plantillas.route("/ofi_plantillas/recuperar/<ofi_plantilla_id>")
@permission_required(MODULO, Permiso.ADMINISTRAR)
def recover(ofi_plantilla_id):
    """Recuperar Ofi Plantilla"""
    ofi_plantilla_id = safe_uuid(ofi_plantilla_id)
    if not ofi_plantilla_id:
        flash("ID de plantilla inválido", "warning")
        return redirect(url_for("ofi_plantillas.list_active"))
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
