"""
Web Ramas, vistas
"""

import json

from flask import Blueprint, flash, redirect, render_template, request, url_for
from flask_login import current_user, login_required

from hercules.blueprints.bitacoras.models import Bitacora
from hercules.blueprints.modulos.models import Modulo
from hercules.blueprints.permisos.models import Permiso
from hercules.blueprints.usuarios.decorators import permission_required
from hercules.blueprints.web_ramas.forms import WebRamaForm
from hercules.blueprints.web_ramas.models import WebRama
from lib.datatables import get_datatable_parameters, output_datatable_json
from lib.safe_string import safe_clave, safe_message, safe_string

MODULO = "WEB RAMAS"

web_ramas = Blueprint("web_ramas", __name__, template_folder="templates")


@web_ramas.before_request
@login_required
@permission_required(MODULO, Permiso.VER)
def before_request():
    """Permiso por defecto"""


@web_ramas.route("/web_ramas/datatable_json", methods=["GET", "POST"])
def datatable_json():
    """DataTable JSON para listado de WebRamas"""
    # Tomar parámetros de Datatables
    draw, start, rows_per_page = get_datatable_parameters()
    # Consultar
    consulta = WebRama.query
    # Primero filtrar por columnas propias
    if "estatus" in request.form:
        consulta = consulta.filter_by(estatus=request.form["estatus"])
    else:
        consulta = consulta.filter_by(estatus="A")
    if "clave" in request.form:
        consulta = consulta.filter(WebRama.clave.contains(request.form["clave"]))
    if "nombre" in request.form:
        consulta = consulta.filter(WebRama.nombre.contains(request.form["nombre"]))
    # Ordenar y paginar
    registros = consulta.order_by(WebRama.clave).offset(start).limit(rows_per_page).all()
    total = consulta.count()
    # Elaborar datos para DataTable
    data = []
    for resultado in registros:
        data.append(
            {
                "detalle": {
                    "clave": resultado.clave,
                    "url": url_for("web_ramas.detail", web_rama_id=resultado.id),
                },
                "nombre": resultado.nombre,
            }
        )
    # Entregar JSON
    return output_datatable_json(draw, total, data)


@web_ramas.route("/web_ramas")
def list_active():
    """Listado de WebRamas activos"""
    return render_template(
        "web_ramas/list.jinja2",
        filtros=json.dumps({"estatus": "A"}),
        titulo="Ramas",
        estatus="A",
    )


@web_ramas.route("/web_ramas/inactivos")
@permission_required(MODULO, Permiso.ADMINISTRAR)
def list_inactive():
    """Listado de WebRamas inactivos"""
    return render_template(
        "web_ramas/list.jinja2",
        filtros=json.dumps({"estatus": "B"}),
        titulo="Ramas inactivas",
        estatus="B",
    )


@web_ramas.route("/web_ramas/<int:web_rama_id>")
def detail(web_rama_id):
    """Detalle de una WebRama"""
    web_rama = WebRama.query.get_or_404(web_rama_id)
    return render_template("web_ramas/detail.jinja2", web_rama=web_rama)


@web_ramas.route("/web_ramas/nuevo", methods=["GET", "POST"])
@permission_required(MODULO, Permiso.CREAR)
def new():
    """Nuevo WebRama"""
    form = WebRamaForm()
    if form.validate_on_submit():
        # Validar que la clave no está en uso
        clave = safe_clave(form.clave.data)
        if WebRama.query.filter_by(clave=clave).first():
            flash(f"La clave {clave} ya está en uso", "warning")
            return render_template("web_ramas/new.jinja2", form=form)
        # Guardar
        web_rama = WebRama(
            clave=clave,
            nombre=safe_string(form.nombre.data, do_unidecode=False, save_enie=True, to_uppercase=False),
        )
        web_rama.save()
        # Guardar bitácora
        bitacora = Bitacora(
            modulo=Modulo.query.filter_by(nombre=MODULO).first(),
            usuario=current_user,
            descripcion=safe_message(f"Nuevo WebRama {web_rama.clave}"),
            url=url_for("web_ramas.detail", web_rama_id=web_rama.id),
        )
        bitacora.save()
        # Entregar detalle
        flash(bitacora.descripcion, "success")
        return redirect(bitacora.url)
    return render_template("web_ramas/new.jinja2", form=form)


@web_ramas.route("/web_ramas/edicion/<int:web_rama_id>", methods=["GET", "POST"])
@permission_required(MODULO, Permiso.MODIFICAR)
def edit(web_rama_id):
    """Editar WebRama"""
    web_rama = WebRama.query.get_or_404(web_rama_id)
    form = WebRamaForm()
    if form.validate_on_submit():
        es_valido = True
        # Si cambia la clave, validar que la clave no está en uso
        clave = safe_clave(form.clave.data)
        if web_rama.clave != clave and WebRama.query.filter_by(clave=clave).filter(WebRama.id != web_rama_id).first():
            flash("La clave ya está en uso", "warning")
            es_valido = False
        # Si es válido
        if es_valido:
            # Actualizar
            web_rama.clave = clave
            web_rama.nombre = safe_string(form.nombre.data, do_unidecode=False, save_enie=True, to_uppercase=False)
            web_rama.save()
            # Guardar bitácora
            bitacora = Bitacora(
                modulo=Modulo.query.filter_by(nombre=MODULO).first(),
                usuario=current_user,
                descripcion=safe_message(f"Editado WebRama {web_rama.clave}"),
                url=url_for("web_ramas.detail", web_rama_id=web_rama.id),
            )
            bitacora.save()
            # Entregar detalle
            flash(bitacora.descripcion, "success")
            return redirect(bitacora.url)
    form.clave.data = web_rama.clave
    form.nombre.data = web_rama.nombre
    return render_template("web_ramas/edit.jinja2", form=form, web_rama=web_rama)


@web_ramas.route("/web_ramas/eliminar/<int:web_rama_id>")
@permission_required(MODULO, Permiso.ADMINISTRAR)
def delete(web_rama_id):
    """Eliminar WebRama"""
    web_rama = WebRama.query.get_or_404(web_rama_id)
    if web_rama.estatus == "A":
        web_rama.delete()
        bitacora = Bitacora(
            modulo=Modulo.query.filter_by(nombre=MODULO).first(),
            usuario=current_user,
            descripcion=safe_message(f"Eliminado Rama {web_rama.clave}"),
            url=url_for("web_ramas.detail", web_rama_id=web_rama.id),
        )
        bitacora.save()
        flash(bitacora.descripcion, "success")
    return redirect(url_for("web_ramas.detail", web_rama_id=web_rama.id))


@web_ramas.route("/web_ramas/recuperar/<int:web_rama_id>")
@permission_required(MODULO, Permiso.ADMINISTRAR)
def recover(web_rama_id):
    """Recuperar WebRama"""
    web_rama = WebRama.query.get_or_404(web_rama_id)
    if web_rama.estatus == "B":
        web_rama.recover()
        bitacora = Bitacora(
            modulo=Modulo.query.filter_by(nombre=MODULO).first(),
            usuario=current_user,
            descripcion=safe_message(f"Recuperado Rama {web_rama.clave}"),
            url=url_for("web_ramas.detail", web_rama_id=web_rama.id),
        )
        bitacora.save()
        flash(bitacora.descripcion, "success")
    return redirect(url_for("web_ramas.detail", web_rama_id=web_rama.id))
