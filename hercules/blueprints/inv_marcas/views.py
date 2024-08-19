"""
Inventarios Marcas, vistas
"""

import json

from flask import Blueprint, flash, redirect, render_template, request, url_for
from flask_login import current_user, login_required

from hercules.blueprints.bitacoras.models import Bitacora
from hercules.blueprints.inv_marcas.forms import InvMarcaForm
from hercules.blueprints.inv_marcas.models import InvMarca
from hercules.blueprints.modulos.models import Modulo
from hercules.blueprints.permisos.models import Permiso
from hercules.blueprints.usuarios.decorators import permission_required
from lib.datatables import get_datatable_parameters, output_datatable_json
from lib.safe_string import safe_message, safe_string

MODULO = "INV MARCAS"

inv_marcas = Blueprint("inv_marcas", __name__, template_folder="templates")


@inv_marcas.before_request
@login_required
@permission_required(MODULO, Permiso.VER)
def before_request():
    """Permiso por defecto"""


@inv_marcas.route("/inv_marcas/datatable_json", methods=["GET", "POST"])
def datatable_json():
    """DataTable JSON para listado de InvMarca"""
    # Tomar parámetros de Datatables
    draw, start, rows_per_page = get_datatable_parameters()
    # Consultar
    consulta = InvMarca.query
    # Primero filtrar por columnas propias
    if "estatus" in request.form:
        consulta = consulta.filter_by(estatus=request.form["estatus"])
    else:
        consulta = consulta.filter_by(estatus="A")
    if "nombre" in request.form:
        nombre = safe_string(request.form["nombre"])
        if nombre != "":
            consulta = consulta.filter(InvMarca.nombre.contains(nombre))
    # Ordenar y paginar
    registros = consulta.order_by(InvMarca.nombre).offset(start).limit(rows_per_page).all()
    total = consulta.count()
    # Elaborar datos para DataTable
    data = []
    for resultado in registros:
        data.append(
            {
                "detalle": {
                    "nombre": resultado.nombre,
                    "url": url_for("inv_marcas.detail", inv_marca_id=resultado.id),
                },
            }
        )
    # Entregar JSON
    return output_datatable_json(draw, total, data)


@inv_marcas.route("/inv_marcas")
def list_active():
    """Listado de InvMarca activas"""
    return render_template(
        "inv_marcas/list.jinja2",
        filtros=json.dumps({"estatus": "A"}),
        titulo="Marcas",
        estatus="A",
    )


@inv_marcas.route("/inv_marcas/inactivos")
@permission_required(MODULO, Permiso.ADMINISTRAR)
def list_inactive():
    """Listado de InvMarca inactivas"""
    return render_template(
        "inv_marcas/list.jinja2",
        filtros=json.dumps({"estatus": "B"}),
        titulo="Marcas inactivas",
        estatus="B",
    )


@inv_marcas.route("/inv_marcas/<int:inv_marca_id>")
def detail(inv_marca_id):
    """Detalle de una InvMarca"""
    inv_marca = InvMarca.query.get_or_404(inv_marca_id)
    return render_template("inv_marcas/detail.jinja2", inv_marca=inv_marca)


@inv_marcas.route("/inv_marcas/nuevo", methods=["GET", "POST"])
@permission_required(MODULO, Permiso.CREAR)
def new():
    """Nueva InvMarca"""
    form = InvMarcaForm()
    if form.validate_on_submit():
        # Validar que el nombre no está en uso
        nombre = safe_string(form.nombre.data, save_enie=True)
        if InvMarca.query.filter_by(nombre=nombre).first():
            flash(f"El nombre {nombre} ya está en uso", "warning")
            return render_template("inv_marcas/new.jinja2", form=form)
        # Guardar
        inv_marca = InvMarca(nombre=nombre)
        inv_marca.save()
        # Guardar bitácora
        bitacora = Bitacora(
            modulo=Modulo.query.filter_by(nombre=MODULO).first(),
            usuario=current_user,
            descripcion=safe_message(f"Nueva InvMarca {inv_marca.nombre}"),
            url=url_for("inv_marcas.detail", inv_marca_id=inv_marca.id),
        )
        bitacora.save()
        # Entregar detalle
        flash(bitacora.descripcion, "success")
        return redirect(bitacora.url)
    return render_template("inv_marcas/new.jinja2", form=form)


@inv_marcas.route("/inv_marcas/edicion/<int:inv_marca_id>", methods=["GET", "POST"])
@permission_required(MODULO, Permiso.MODIFICAR)
def edit(inv_marca_id):
    """Editar InvMarca"""
    inv_marca = InvMarca.query.get_or_404(inv_marca_id)
    form = InvMarcaForm()
    if form.validate_on_submit():
        es_valido = True
        # Si cambia el nombre, validar que el nombre no está en uso
        nombre = safe_string(form.nombre.data, save_enie=True)
        if inv_marca.nombre != nombre and InvMarca.query.filter_by(nombre=nombre).first():
            flash("La nombre ya está en uso", "warning")
            es_valido = False
        # Si es válido
        if es_valido:
            # Guardar
            inv_marca.nombre = nombre
            inv_marca.save()
            # Guardar bitácora
            bitacora = Bitacora(
                modulo=Modulo.query.filter_by(nombre=MODULO).first(),
                usuario=current_user,
                descripcion=safe_message(f"Editado InvMarca {inv_marca.nombre}"),
                url=url_for("inv_marcas.detail", inv_marca_id=inv_marca.id),
            )
            bitacora.save()
            # Entregar detalle
            flash(bitacora.descripcion, "success")
            return redirect(bitacora.url)
    form.nombre.data = inv_marca.nombre
    return render_template("inv_marcas/edit.jinja2", form=form, inv_marca=inv_marca)


@inv_marcas.route("/inv_marcas/eliminar/<int:inv_marca_id>")
@permission_required(MODULO, Permiso.ADMINISTRAR)
def delete(inv_marca_id):
    """Eliminar InvMarca"""
    inv_marca = InvMarca.query.get_or_404(inv_marca_id)
    if inv_marca.estatus == "A":
        inv_marca.delete()
        bitacora = Bitacora(
            modulo=Modulo.query.filter_by(nombre=MODULO).first(),
            usuario=current_user,
            descripcion=safe_message(f"Eliminado InvMarca {inv_marca.nombre}"),
            url=url_for("inv_marcas.detail", inv_marca_id=inv_marca.id),
        )
        bitacora.save()
        flash(bitacora.descripcion, "success")
    return redirect(url_for("inv_marcas.detail", inv_marca_id=inv_marca.id))


@inv_marcas.route("/inv_marcas/recuperar/<int:inv_marca_id>")
@permission_required(MODULO, Permiso.ADMINISTRAR)
def recover(inv_marca_id):
    """Recuperar InvMarca"""
    inv_marca = InvMarca.query.get_or_404(inv_marca_id)
    if inv_marca.estatus == "B":
        inv_marca.recover()
        bitacora = Bitacora(
            modulo=Modulo.query.filter_by(nombre=MODULO).first(),
            usuario=current_user,
            descripcion=safe_message(f"Recuperado InvMarca {inv_marca.nombre}"),
            url=url_for("inv_marcas.detail", inv_marca_id=inv_marca.id),
        )
        bitacora.save()
        flash(bitacora.descripcion, "success")
    return redirect(url_for("inv_marcas.detail", inv_marca_id=inv_marca.id))
