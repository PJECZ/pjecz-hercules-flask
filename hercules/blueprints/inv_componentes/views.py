"""
Inventarios Componentes, vistas
"""

import json

from flask import Blueprint, flash, redirect, render_template, request, url_for
from flask_login import current_user, login_required

from hercules.blueprints.bitacoras.models import Bitacora
from hercules.blueprints.inv_componentes.forms import InvComponenteForm
from hercules.blueprints.inv_componentes.models import InvComponente
from hercules.blueprints.inv_equipos.models import InvEquipo
from hercules.blueprints.modulos.models import Modulo
from hercules.blueprints.permisos.models import Permiso
from hercules.blueprints.usuarios.decorators import permission_required
from lib.datatables import get_datatable_parameters, output_datatable_json
from lib.safe_string import safe_message, safe_string

MODULO = "INV COMPONENTES"

inv_componentes = Blueprint("inv_componentes", __name__, template_folder="templates")


@inv_componentes.before_request
@login_required
@permission_required(MODULO, Permiso.VER)
def before_request():
    """Permiso por defecto"""


@inv_componentes.route("/inv_componentes/datatable_json", methods=["GET", "POST"])
def datatable_json():
    """DataTable JSON para listado de InvComponente"""
    # Tomar parámetros de Datatables
    draw, start, rows_per_page = get_datatable_parameters()
    # Consultar
    consulta = InvComponente.query
    # Primero filtrar por columnas propias
    if "estatus" in request.form:
        consulta = consulta.filter_by(estatus=request.form["estatus"])
    else:
        consulta = consulta.filter_by(estatus="A")
    if "inv_categoria_id" in request.form:
        consulta = consulta.filter_by(inv_categoria_id=request.form["inv_categoria_id"])
    if "inv_equipo_id" in request.form:
        consulta = consulta.filter_by(inv_equipo_id=request.form["inv_equipo_id"])
    if "descripcion" in request.form:
        descripcion = safe_string(request.form["descripcion"])
        if descripcion != "":
            consulta = consulta.filter(InvComponente.descripcion.contains(descripcion))
    # Ordenar y paginar
    registros = consulta.order_by(InvComponente.id).offset(start).limit(rows_per_page).all()
    total = consulta.count()
    # Elaborar datos para DataTable
    data = []
    for resultado in registros:
        data.append(
            {
                "detalle": {
                    "id": resultado.id,
                    "url": url_for("inv_componentes.detail", inv_componente_id=resultado.id),
                },
                "inv_categoria": {
                    "nombre": resultado.inv_categoria.nombre,
                    "url": (
                        url_for("inv_categorias.detail", inv_categoria_id=resultado.inv_categoria_id)
                        if current_user.can_view("INV CATEGORIAS")
                        else ""
                    ),
                },
                "descripcion": resultado.descripcion,
                "cantidad": resultado.cantidad,
                "generacion": resultado.generacion,
                "version": resultado.version,
            }
        )
    # Entregar JSON
    return output_datatable_json(draw, total, data)


@inv_componentes.route("/inv_componentes")
def list_active():
    """Listado de InvComponente activos"""
    return render_template(
        "inv_componentes/list.jinja2",
        filtros=json.dumps({"estatus": "A"}),
        titulo="Componentes",
        estatus="A",
    )


@inv_componentes.route("/inv_componentes/inactivos")
@permission_required(MODULO, Permiso.ADMINISTRAR)
def list_inactive():
    """Listado de InvComponente inactivos"""
    return render_template(
        "inv_componentes/list.jinja2",
        filtros=json.dumps({"estatus": "B"}),
        titulo="Componentes inactivos",
        estatus="B",
    )


@inv_componentes.route("/inv_componentes/<int:inv_componente_id>")
def detail(inv_componente_id):
    """Detalle de un InvComponente"""
    inv_componente = InvComponente.query.get_or_404(inv_componente_id)
    return render_template("inv_componentes/detail.jinja2", inv_componente=inv_componente)


@inv_componentes.route("/inv_componentes/nuevo/<int:inv_equipo_id>", methods=["GET", "POST"])
@permission_required(MODULO, Permiso.CREAR)
def new_with_inv_equipo_id(inv_equipo_id):
    """Nuevo InvComponente"""
    inv_equipo = InvEquipo.query.get_or_404(inv_equipo_id)
    form = InvComponenteForm()
    if form.validate_on_submit():
        # Guardar
        inv_componente = InvComponente(
            inv_equipo_id=inv_equipo.id,
            inv_categoria_id=form.inv_categoria.data,
            descripcion=safe_string(form.descripcion.data, save_enie=True),
            cantidad=form.cantidad.data,
            generacion=form.generacion.data,
            version=safe_string(form.version.data, save_enie=True),
        )
        inv_componente.save()
        # Guardar bitácora
        bitacora = Bitacora(
            modulo=Modulo.query.filter_by(nombre=MODULO).first(),
            usuario=current_user,
            descripcion=safe_message(f"Nuevo InvComponente {inv_componente.descripcion}"),
            url=url_for("inv_componentes.detail", inv_componente_id=inv_componente.id),
        )
        bitacora.save()
        # Despues de guardar ir al detalle del InvEquipo
        flash(bitacora.descripcion, "success")
        return redirect(url_for("inv_equipos.detail", inv_equipo_id=inv_equipo.id))
    return render_template("inv_componentes/new.jinja2", form=form, inv_equipo=inv_equipo)


@inv_componentes.route("/inv_componentes/edicion/<int:inv_componente_id>", methods=["GET", "POST"])
@permission_required(MODULO, Permiso.MODIFICAR)
def edit(inv_componente_id):
    """Editar InvComponente"""
    inv_componente = InvComponente.query.get_or_404(inv_componente_id)
    form = InvComponenteForm()
    if form.validate_on_submit():
        # Guardar
        inv_componente.inv_categoria_id = form.inv_categoria.data
        inv_componente.descripcion = safe_string(form.descripcion.data, save_enie=True)
        inv_componente.cantidad = form.cantidad.data
        inv_componente.generacion = form.generacion.data
        inv_componente.version = safe_string(form.version.data, save_enie=True)
        inv_componente.save()
        # Guardar bitácora
        bitacora = Bitacora(
            modulo=Modulo.query.filter_by(nombre=MODULO).first(),
            usuario=current_user,
            descripcion=safe_message(f"Editado InvComponente {inv_componente.id}"),
            url=url_for("inv_componentes.detail", inv_componente_id=inv_componente.id),
        )
        bitacora.save()
        # Entregar detalle
        flash(bitacora.descripcion, "success")
        return redirect(bitacora.url)
    form.inv_categoria.data = inv_componente.inv_categoria_id  # Usa id porque es un SelectField
    form.descripcion.data = inv_componente.descripcion
    form.cantidad.data = inv_componente.cantidad
    form.generacion.data = inv_componente.generacion
    form.version.data = inv_componente.version
    return render_template("inv_componentes/edit.jinja2", form=form, inv_componente=inv_componente)


@inv_componentes.route("/inv_componentes/eliminar/<int:inv_componente_id>")
@permission_required(MODULO, Permiso.ADMINISTRAR)
def delete(inv_componente_id):
    """Eliminar InvComponente"""
    inv_componente = InvComponente.query.get_or_404(inv_componente_id)
    if inv_componente.estatus == "A":
        inv_componente.delete()
        bitacora = Bitacora(
            modulo=Modulo.query.filter_by(nombre=MODULO).first(),
            usuario=current_user,
            descripcion=safe_message(f"Eliminado InvComponente {inv_componente.id}"),
            url=url_for("inv_componentes.detail", inv_componente_id=inv_componente.id),
        )
        bitacora.save()
        flash(bitacora.descripcion, "success")
    return redirect(url_for("inv_componentes.detail", inv_componente_id=inv_componente.id))


@inv_componentes.route("/inv_componentes/recuperar/<int:inv_componente_id>")
@permission_required(MODULO, Permiso.ADMINISTRAR)
def recover(inv_componente_id):
    """Recuperar InvComponente"""
    inv_componente = InvComponente.query.get_or_404(inv_componente_id)
    if inv_componente.estatus == "B":
        inv_componente.recover()
        bitacora = Bitacora(
            modulo=Modulo.query.filter_by(nombre=MODULO).first(),
            usuario=current_user,
            descripcion=safe_message(f"Recuperado InvComponente {inv_componente.id}"),
            url=url_for("inv_componentes.detail", inv_componente_id=inv_componente.id),
        )
        bitacora.save()
        flash(bitacora.descripcion, "success")
    return redirect(url_for("inv_componentes.detail", inv_componente_id=inv_componente.id))
