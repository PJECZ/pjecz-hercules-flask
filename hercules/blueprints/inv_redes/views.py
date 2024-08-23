"""
Inventarios Redes, vistas
"""

import json

from flask import Blueprint, flash, redirect, render_template, request, url_for
from flask_login import current_user, login_required

from hercules.blueprints.bitacoras.models import Bitacora
from hercules.blueprints.inv_redes.forms import InvRedForm
from hercules.blueprints.inv_redes.models import InvRed
from hercules.blueprints.modulos.models import Modulo
from hercules.blueprints.permisos.models import Permiso
from hercules.blueprints.usuarios.decorators import permission_required
from lib.datatables import get_datatable_parameters, output_datatable_json
from lib.safe_string import safe_message, safe_string

MODULO = "INV REDES"

inv_redes = Blueprint("inv_redes", __name__, template_folder="templates")


@inv_redes.before_request
@login_required
@permission_required(MODULO, Permiso.VER)
def before_request():
    """Permiso por defecto"""


@inv_redes.route("/inv_redes/datatable_json", methods=["GET", "POST"])
def datatable_json():
    """DataTable JSON para listado de InvRed"""
    # Tomar parámetros de Datatables
    draw, start, rows_per_page = get_datatable_parameters()
    # Consultar
    consulta = InvRed.query
    # Primero filtrar por columnas propias
    if "estatus" in request.form:
        consulta = consulta.filter_by(estatus=request.form["estatus"])
    else:
        consulta = consulta.filter_by(estatus="A")
    if "nombre" in request.form:
        nombre = safe_string(request.form["nombre"])
        if nombre != "":
            consulta = consulta.filter(InvRed.nombre.contains(nombre))
    if "tipo" in request.form:
        tipo = safe_string(request.form["tipo"])
        if tipo != "":
            consulta = consulta.filter(InvRed.tipo == tipo)
    # Ordenar y paginar
    registros = consulta.order_by(InvRed.id).offset(start).limit(rows_per_page).all()
    total = consulta.count()
    # Elaborar datos para DataTable
    data = []
    for resultado in registros:
        data.append(
            {
                "detalle": {
                    "nombre": resultado.nombre,
                    "url": url_for("inv_redes.detail", inv_red_id=resultado.id),
                },
                "tipo": resultado.tipo,
            }
        )
    # Entregar JSON
    return output_datatable_json(draw, total, data)


@inv_redes.route("/inv_redes")
def list_active():
    """Listado de InvRed activas"""
    return render_template(
        "inv_redes/list.jinja2",
        filtros=json.dumps({"estatus": "A"}),
        titulo="Redes",
        estatus="A",
    )


@inv_redes.route("/inv_redes/inactivos")
@permission_required(MODULO, Permiso.ADMINISTRAR)
def list_inactive():
    """Listado de InvRed inactivas"""
    return render_template(
        "inv_redes/list.jinja2",
        filtros=json.dumps({"estatus": "B"}),
        titulo="Redes inactivas",
        estatus="B",
    )


@inv_redes.route("/inv_redes/<int:inv_red_id>")
def detail(inv_red_id):
    """Detalle de una InvRed"""
    inv_red = InvRed.query.get_or_404(inv_red_id)
    return render_template("inv_redes/detail.jinja2", inv_red=inv_red)


@inv_redes.route("/inv_redes/nuevo", methods=["GET", "POST"])
@permission_required(MODULO, Permiso.CREAR)
def new():
    """Nueva InvRed"""
    form = InvRedForm()
    if form.validate_on_submit():
        # Validar que el nombre no está en uso
        nombre = safe_string(form.nombre.data, save_enie=True)
        if InvRed.query.filter_by(nombre=nombre).first():
            flash(f"El nombre {nombre} ya está en uso", "warning")
            return render_template("inv_redes/new.jinja2", form=form)
        # Guardar
        inv_red = InvRed(
            nombre=nombre,
            tipo=form.tipo.data,
        )
        inv_red.save()
        # Guardar bitácora
        bitacora = Bitacora(
            modulo=Modulo.query.filter_by(nombre=MODULO).first(),
            usuario=current_user,
            descripcion=safe_message(f"Nueva InvRed {inv_red.nombre}"),
            url=url_for("inv_redes.detail", inv_red_id=inv_red.id),
        )
        bitacora.save()
        # Entregar detalle
        flash(bitacora.descripcion, "success")
        return redirect(bitacora.url)
    return render_template("inv_redes/new.jinja2", form=form)


@inv_redes.route("/inv_redes/edicion/<int:inv_red_id>", methods=["GET", "POST"])
@permission_required(MODULO, Permiso.MODIFICAR)
def edit(inv_red_id):
    """Editar InvRed"""
    inv_red = InvRed.query.get_or_404(inv_red_id)
    form = InvRedForm()
    if form.validate_on_submit():
        es_valido = True
        # Si cambia el nombre, validar que el nombre no está en uso
        nombre = safe_string(form.nombre.data, save_enie=True)
        if inv_red.nombre != nombre and InvRed.query.filter_by(nombre=nombre).first():
            flash("El nombre ya está en uso", "warning")
            es_valido = False
        # Si es válido
        if es_valido:
            # Guardar
            inv_red.nombre = nombre
            inv_red.tipo = form.tipo.data
            inv_red.save()
            # Guardar bitácora
            bitacora = Bitacora(
                modulo=Modulo.query.filter_by(nombre=MODULO).first(),
                usuario=current_user,
                descripcion=safe_message(f"Editado InvRed {inv_red.nombre}"),
                url=url_for("inv_redes.detail", inv_red_id=inv_red.id),
            )
            bitacora.save()
            # Entregar detalle
            flash(bitacora.descripcion, "success")
            return redirect(bitacora.url)
    form.nombre.data = inv_red.nombre
    form.tipo.data = inv_red.tipo
    return render_template("inv_redes/edit.jinja2", form=form, inv_red=inv_red)


@inv_redes.route("/inv_redes/eliminar/<int:inv_red_id>")
@permission_required(MODULO, Permiso.ADMINISTRAR)
def delete(inv_red_id):
    """Eliminar InvRed"""
    inv_red = InvRed.query.get_or_404(inv_red_id)
    if inv_red.estatus == "A":
        inv_red.delete()
        bitacora = Bitacora(
            modulo=Modulo.query.filter_by(nombre=MODULO).first(),
            usuario=current_user,
            descripcion=safe_message(f"Eliminado InvRed {inv_red.nombre}"),
            url=url_for("inv_redes.detail", inv_red_id=inv_red.id),
        )
        bitacora.save()
        flash(bitacora.descripcion, "success")
    return redirect(url_for("inv_redes.detail", inv_red_id=inv_red.id))


@inv_redes.route("/inv_redes/recuperar/<int:inv_red_id>")
@permission_required(MODULO, Permiso.ADMINISTRAR)
def recover(inv_red_id):
    """Recuperar InvRed"""
    inv_red = InvRed.query.get_or_404(inv_red_id)
    if inv_red.estatus == "B":
        inv_red.recover()
        bitacora = Bitacora(
            modulo=Modulo.query.filter_by(nombre=MODULO).first(),
            usuario=current_user,
            descripcion=safe_message(f"Recuperado InvRed {inv_red.nombre}"),
            url=url_for("inv_redes.detail", inv_red_id=inv_red.id),
        )
        bitacora.save()
        flash(bitacora.descripcion, "success")
    return redirect(url_for("inv_redes.detail", inv_red_id=inv_red.id))
