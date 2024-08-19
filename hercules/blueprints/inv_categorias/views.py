"""
Inventarios Categorias, vistas
"""

import json

from flask import Blueprint, flash, redirect, render_template, request, url_for
from flask_login import current_user, login_required

from hercules.blueprints.bitacoras.models import Bitacora
from hercules.blueprints.inv_categorias.forms import InvCategoriaForm
from hercules.blueprints.inv_categorias.models import InvCategoria
from hercules.blueprints.modulos.models import Modulo
from hercules.blueprints.permisos.models import Permiso
from hercules.blueprints.usuarios.decorators import permission_required
from lib.datatables import get_datatable_parameters, output_datatable_json
from lib.safe_string import safe_message, safe_string

MODULO = "INV CATEGORIAS"

inv_categorias = Blueprint("inv_categorias", __name__, template_folder="templates")


@inv_categorias.before_request
@login_required
@permission_required(MODULO, Permiso.VER)
def before_request():
    """Permiso por defecto"""


@inv_categorias.route("/inv_categorias/datatable_json", methods=["GET", "POST"])
def datatable_json():
    """DataTable JSON para listado de InvCategoria"""
    # Tomar parámetros de Datatables
    draw, start, rows_per_page = get_datatable_parameters()
    # Consultar
    consulta = InvCategoria.query
    # Primero filtrar por columnas propias
    if "estatus" in request.form:
        consulta = consulta.filter_by(estatus=request.form["estatus"])
    else:
        consulta = consulta.filter_by(estatus="A")
    # Luego filtrar por columnas de otras tablas
    if "nombre" in request.form:
        nombre = safe_string(request.form["nombre"])
        if nombre != "":
            consulta = consulta.filter(InvCategoria.nombre.contains(nombre))
    # Ordenar y paginar
    registros = consulta.order_by(InvCategoria.id).offset(start).limit(rows_per_page).all()
    total = consulta.count()
    # Elaborar datos para DataTable
    data = []
    for resultado in registros:
        data.append(
            {
                "detalle": {
                    "nombre": resultado.nombre,
                    "url": url_for("inv_categorias.detail", inv_categoria_id=resultado.id),
                },
            }
        )
    # Entregar JSON
    return output_datatable_json(draw, total, data)


@inv_categorias.route("/inv_categorias")
def list_active():
    """Listado de InvCategoria activas"""
    return render_template(
        "inv_categorias/list.jinja2",
        filtros=json.dumps({"estatus": "A"}),
        titulo="Categorias",
        estatus="A",
    )


@inv_categorias.route("/inv_categorias/inactivos")
@permission_required(MODULO, Permiso.ADMINISTRAR)
def list_inactive():
    """Listado de InvCategoria inactivas"""
    return render_template(
        "inv_categorias/list.jinja2",
        filtros=json.dumps({"estatus": "B"}),
        titulo="Categorias inactivas",
        estatus="B",
    )


@inv_categorias.route("/inv_categorias/<int:inv_categoria_id>")
def detail(inv_categoria_id):
    """Detalle de una InvCategoria"""
    inv_categoria = InvCategoria.query.get_or_404(inv_categoria_id)
    return render_template("inv_categorias/detail.jinja2", inv_categoria=inv_categoria)


@inv_categorias.route("/inv_categorias/nuevo", methods=["GET", "POST"])
@permission_required(MODULO, Permiso.CREAR)
def new():
    """Nueva InvCategoria"""
    form = InvCategoriaForm()
    if form.validate_on_submit():
        # Validar que el nombre no está en uso
        nombre = safe_string(form.nombre.data, save_enie=True)
        if InvCategoria.query.filter_by(nombre=nombre).first():
            flash(f"El nombre {nombre} ya está en uso", "warning")
            return render_template("inv_categorias/new.jinja2", form=form)
        # Guardar
        inv_categoria = InvCategoria(nombre=nombre)
        inv_categoria.save()
        # Guardar bitácora
        bitacora = Bitacora(
            modulo=Modulo.query.filter_by(nombre=MODULO).first(),
            usuario=current_user,
            descripcion=safe_message(f"Nueva InvCategoria {inv_categoria.nombre}"),
            url=url_for("inv_categorias.detail", inv_categoria_id=inv_categoria.id),
        )
        bitacora.save()
        # Entregar detalle
        flash(bitacora.descripcion, "success")
        return redirect(bitacora.url)
    return render_template("inv_categorias/new.jinja2", form=form)


@inv_categorias.route("/inv_categorias/edicion/<int:inv_categoria_id>", methods=["GET", "POST"])
@permission_required(MODULO, Permiso.MODIFICAR)
def edit(inv_categoria_id):
    """Editar InvCategoria"""
    inv_categoria = InvCategoria.query.get_or_404(inv_categoria_id)
    form = InvCategoriaForm()
    if form.validate_on_submit():
        es_valido = True
        # Si cambia el nombre, validar que el nombre no está en uso
        nombre = safe_string(form.nombre.data, save_enie=True)
        if inv_categoria.nombre != nombre and InvCategoria.query.filter_by(nombre=nombre).first():
            flash("El nombre ya está en uso", "warning")
            es_valido = False
        # Si es válido
        if es_valido:
            # Guardar
            inv_categoria.nombre = nombre
            inv_categoria.save()
            # Guardar bitácora
            bitacora = Bitacora(
                modulo=Modulo.query.filter_by(nombre=MODULO).first(),
                usuario=current_user,
                descripcion=safe_message(f"Editado InvCategoria {inv_categoria.nombre}"),
                url=url_for("inv_categorias.detail", inv_categoria_id=inv_categoria.id),
            )
            bitacora.save()
            # Entregar detalle
            flash(bitacora.descripcion, "success")
            return redirect(bitacora.url)
    form.nombre.data = inv_categoria.nombre
    return render_template("inv_categorias/edit.jinja2", form=form, inv_categoria=inv_categoria)


@inv_categorias.route("/inv_categorias/eliminar/<int:inv_categoria_id>")
@permission_required(MODULO, Permiso.ADMINISTRAR)
def delete(inv_categoria_id):
    """Eliminar InvCategoria"""
    inv_categoria = InvCategoria.query.get_or_404(inv_categoria_id)
    if inv_categoria.estatus == "A":
        inv_categoria.delete()
        bitacora = Bitacora(
            modulo=Modulo.query.filter_by(nombre=MODULO).first(),
            usuario=current_user,
            descripcion=safe_message(f"Eliminado InvCategoria {inv_categoria.nombre}"),
            url=url_for("inv_categorias.detail", inv_categoria_id=inv_categoria.id),
        )
        bitacora.save()
        flash(bitacora.descripcion, "success")
    return redirect(url_for("inv_categorias.detail", inv_categoria_id=inv_categoria.id))


@inv_categorias.route("/inv_categorias/recuperar/<int:inv_categoria_id>")
@permission_required(MODULO, Permiso.ADMINISTRAR)
def recover(inv_categoria_id):
    """Recuperar InvCategoria"""
    inv_categoria = InvCategoria.query.get_or_404(inv_categoria_id)
    if inv_categoria.estatus == "B":
        inv_categoria.recover()
        bitacora = Bitacora(
            modulo=Modulo.query.filter_by(nombre=MODULO).first(),
            usuario=current_user,
            descripcion=safe_message(f"Recuperado InvCategoria {inv_categoria.nombre}"),
            url=url_for("inv_categorias.detail", inv_categoria_id=inv_categoria.id),
        )
        bitacora.save()
        flash(bitacora.descripcion, "success")
    return redirect(url_for("inv_categorias.detail", inv_categoria_id=inv_categoria.id))
