"""
Req Categorías, vistas
"""

import json
from flask import Blueprint, flash, redirect, render_template, request, url_for
from flask_login import current_user, login_required

from lib.datatables import get_datatable_parameters, output_datatable_json
from lib.safe_string import safe_string, safe_message, safe_clave

from hercules.blueprints.bitacoras.models import Bitacora
from hercules.blueprints.modulos.models import Modulo
from hercules.blueprints.permisos.models import Permiso
from hercules.blueprints.usuarios.decorators import permission_required
from hercules.blueprints.req_categorias.models import ReqCategoria
from hercules.blueprints.req_categorias.forms import ReqCategoriaForm


MODULO = "REQ CATEGORIAS"

req_categorias = Blueprint("req_categorias", __name__, template_folder="templates")


@req_categorias.before_request
@login_required
@permission_required(MODULO, Permiso.VER)
def before_request():
    """Permiso por defecto"""


@req_categorias.route("/req_categorias/datatable_json", methods=["GET", "POST"])
def datatable_json():
    """DataTable JSON para listado de Req Categorías"""
    # Tomar parámetros de Datatables
    draw, start, rows_per_page = get_datatable_parameters()
    # Consultar
    consulta = ReqCategoria.query
    # Primero filtrar por columnas propias
    if "estatus" in request.form:
        consulta = consulta.filter_by(estatus=request.form["estatus"])
    else:
        consulta = consulta.filter_by(estatus="A")
    if "clave" in request.form:
        clave = safe_clave(request.form["clave"])
        if clave:
            consulta = consulta.filter(ReqCategoria.clave.contains(clave))
    if "descripcion" in request.form:
        descripcion = safe_string(request.form["descripcion"])
        if descripcion:
            consulta = consulta.filter(ReqCategoria.descripcion.contains(descripcion))
    # Ordenar y paginar
    registros = consulta.order_by(ReqCategoria.clave).offset(start).limit(rows_per_page).all()
    total = consulta.count()
    # Elaborar datos para DataTable
    data = []
    for resultado in registros:
        data.append(
            {
                "detalle": {
                    "clave": resultado.clave,
                    "url": url_for("req_categorias.detail", req_categoria_id=resultado.id),
                },
                "descripcion": resultado.descripcion,
                "btn_agregar_catalogo": url_for("req_catalogos.new_with_categoria", req_categoria_id=resultado.id),
            }
        )
    # Entregar JSON
    return output_datatable_json(draw, total, data)


@req_categorias.route("/req_categorias")
def list_active():
    """Listado de Req Categorías activos"""
    return render_template(
        "req_categorias/list.jinja2",
        filtros=json.dumps({"estatus": "A"}),
        titulo="Requisiciones Categorías",
        estatus="A",
    )


@req_categorias.route("/req_categorias/inactivos")
@permission_required(MODULO, Permiso.ADMINISTRAR)
def list_inactive():
    """Listado de Req Categorías inactivos"""
    return render_template(
        "req_categorias/list.jinja2",
        filtros=json.dumps({"estatus": "B"}),
        titulo="Requisiciones Categorías inactivas",
        estatus="B",
    )


@req_categorias.route("/req_categorias/<int:req_categoria_id>")
def detail(req_categoria_id):
    """Detalle de un Req Categoría"""
    req_categoria = ReqCategoria.query.get_or_404(req_categoria_id)
    return render_template("req_categorias/detail.jinja2", req_categoria=req_categoria)


@req_categorias.route("/req_categorias/nuevo", methods=["GET", "POST"])
@permission_required(MODULO, Permiso.CREAR)
def new():
    """Nuevo Req Categoría"""
    form = ReqCategoriaForm()
    if form.validate_on_submit():
        es_valido = True
        # Validar que la clave no exista
        clave = safe_clave(form.clave.data)
        req_categoria_repetida = ReqCategoria.query.filter_by(clave=clave).first()
        if req_categoria_repetida:
            flash(f"La clave '{clave}' ya existe", "warning")
            es_valido = False
        if es_valido:
            req_categoria = ReqCategoria(
                clave=clave,
                descripcion=safe_string(form.descripcion.data),
            )
            req_categoria.save()
            bitacora = Bitacora(
                modulo=Modulo.query.filter_by(nombre=MODULO).first(),
                usuario=current_user,
                descripcion=safe_message(f"Nueva Req Categoría {req_categoria.clave}"),
                url=url_for("req_categorias.detail", req_categoria_id=req_categoria.id),
            )
            bitacora.save()
            flash(bitacora.descripcion, "success")
            return redirect(bitacora.url)
    return render_template("req_categorias/new.jinja2", form=form)


@req_categorias.route("/req_categorias/edicion/<int:req_categoria_id>", methods=["GET", "POST"])
@permission_required(MODULO, Permiso.MODIFICAR)
def edit(req_categoria_id):
    """Editar Req Categoría"""
    req_categoria = ReqCategoria.query.get_or_404(req_categoria_id)
    form = ReqCategoriaForm()
    if form.validate_on_submit():
        es_valido = True
        # Validar que la clave no esté repetida
        clave = safe_clave(form.clave.data)
        clave_repetida = ReqCategoria.query.filter_by(clave=clave).filter(ReqCategoria.id != req_categoria_id).first()
        if clave_repetida:
            flash(f"La clave '{clave}' ya está en uso.", "warning")
            es_valido = False
        if es_valido:
            req_categoria.clave = clave
            req_categoria.descripcion = safe_string(form.descripcion.data)
            req_categoria.save()
            bitacora = Bitacora(
                modulo=Modulo.query.filter_by(nombre=MODULO).first(),
                usuario=current_user,
                descripcion=safe_message(f"Editado Req Categoría {req_categoria.clave}"),
                url=url_for("req_categorias.detail", req_categoria_id=req_categoria.id),
            )
            bitacora.save()
            flash(bitacora.descripcion, "success")
            return redirect(bitacora.url)
    # Cargar datos
    form.clave.data = req_categoria.clave
    form.descripcion.data = req_categoria.descripcion
    # Entregar
    return render_template("req_categorias/edit.jinja2", form=form, req_categoria=req_categoria)


@req_categorias.route("/req_categorias/eliminar/<int:req_categoria_id>")
@permission_required(MODULO, Permiso.ADMINISTRAR)
def delete(req_categoria_id):
    """Eliminar Req Categoría"""
    req_categoria = ReqCategoria.query.get_or_404(req_categoria_id)
    if req_categoria.estatus == "A":
        req_categoria.delete()
        bitacora = Bitacora(
            modulo=Modulo.query.filter_by(nombre=MODULO).first(),
            usuario=current_user,
            descripcion=safe_message(f"Eliminado Req Categoría {req_categoria.clave}"),
            url=url_for("req_categorias.detail", req_categoria_id=req_categoria.id),
        )
        bitacora.save()
        flash(bitacora.descripcion, "success")
    return redirect(url_for("req_categorias.detail", req_categoria_id=req_categoria.id))


@req_categorias.route("/req_categorias/recuperar/<int:req_categoria_id>")
@permission_required(MODULO, Permiso.ADMINISTRAR)
def recover(req_categoria_id):
    """Recuperar Req Categoría"""
    req_categoria = ReqCategoria.query.get_or_404(req_categoria_id)
    if req_categoria.estatus == "B":
        req_categoria.recover()
        bitacora = Bitacora(
            modulo=Modulo.query.filter_by(nombre=MODULO).first(),
            usuario=current_user,
            descripcion=safe_message(f"Recuperado Req Categoría {req_categoria.clave}"),
            url=url_for("req_categorias.detail", req_categoria_id=req_categoria.id),
        )
        bitacora.save()
        flash(bitacora.descripcion, "success")
    return redirect(url_for("req_categorias.detail", req_categoria_id=req_categoria.id))
