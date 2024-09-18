"""
Soportes Categorías, vistas
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
from hercules.blueprints.soportes_categorias.models import SoporteCategoria
from hercules.blueprints.roles.models import Rol
from hercules.blueprints.soportes_tickets.models import SoporteTicket
from hercules.blueprints.soportes_categorias.forms import SoporteCategoriaForm

MODULO = "SOPORTES CATEGORIAS"

soportes_categorias = Blueprint("soportes_categorias", __name__, template_folder="templates")


@soportes_categorias.before_request
@login_required
@permission_required(MODULO, Permiso.VER)
def before_request():
    """Permiso por defecto"""


@soportes_categorias.route("/soportes_categorias/datatable_json", methods=["GET", "POST"])
def datatable_json():
    """DataTable JSON para listado de Soporte Categorías"""
    # Tomar parámetros de Datatables
    draw, start, rows_per_page = get_datatable_parameters()
    # Consultar
    consulta = SoporteCategoria.query
    # Primero filtrar por columnas propias
    if "estatus" in request.form:
        consulta = consulta.filter(SoporteCategoria.estatus == request.form["estatus"])
    else:
        consulta = consulta.filter(SoporteCategoria.estatus == "A")
    if "nombre" in request.form:
        nombre = safe_string(request.form["nombre"], save_enie=True)
        if nombre != "":
            consulta = consulta.filter(SoporteCategoria.nombre.contains(nombre))
    if "departamento" in request.form:
        consulta = consulta.filter(SoporteCategoria.departamento == request.form["departamento"])
    # Luego filtrar por columnas de otras tablas
    if "atendido_por" in request.form:
        rol = safe_string(request.form["atendido_por"])
        if rol != "":
            consulta = consulta.join(Rol)
            consulta = consulta.filter(Rol.nombre.contains(rol))
    # Ordenar y paginar
    registros = consulta.order_by(SoporteCategoria.nombre).offset(start).limit(rows_per_page).all()
    total = consulta.count()
    # Elaborar datos para DataTable
    data = []
    for resultado in registros:
        data.append(
            {
                "detalle": {
                    "nombre": resultado.nombre,
                    "url": url_for("soportes_categorias.detail", soporte_categoria_id=resultado.id),
                },
                "atendido_por": resultado.rol.nombre,
                "departamento": resultado.departamento,
            }
        )
    # Entregar JSON
    return output_datatable_json(draw, total, data)


@soportes_categorias.route("/soportes_categorias")
def list_active():
    """Listado de Soporte Categorías activos"""
    return render_template(
        "soportes_categorias/list.jinja2",
        filtros=json.dumps({"estatus": "A"}),
        titulo="Soportes Categorías",
        departamentos=SoporteCategoria.DEPARTAMENTOS,
        estatus="A",
    )


@soportes_categorias.route("/soportes_categorias/inactivos")
@permission_required(MODULO, Permiso.ADMINISTRAR)
def list_inactive():
    """Listado de Categorías inactivos"""
    return render_template(
        "soportes_categorias/list.jinja2",
        filtros=json.dumps({"estatus": "B"}),
        titulo="Soportes Categorías Inactivas",
        departamentos=SoporteCategoria.DEPARTAMENTOS,
        estatus="B",
    )


@soportes_categorias.route("/soportes_categorias/<int:soporte_categoria_id>")
def detail(soporte_categoria_id):
    """Detalle de un Soporte Categoría"""
    categoria = SoporteCategoria.query.get_or_404(soporte_categoria_id)
    return render_template("soportes_categorias/detail.jinja2", categoria=categoria, estados=SoporteTicket.ESTADOS)


@soportes_categorias.route("/soportes_categorias/nuevo", methods=["GET", "POST"])
@permission_required(MODULO, Permiso.CREAR)
def new():
    """Nuevo Soporte Categoría"""
    form = SoporteCategoriaForm()
    if form.validate_on_submit():
        # Validar nombre repetido
        nombre = safe_string(form.nombre.data, save_enie=True)
        nombre_repetido = SoporteCategoria.query.filter_by(nombre=nombre).first()
        if nombre_repetido:
            flash("Este nombre ya está en uso, utilice otro.", "warning")
            return render_template("soportes_categorias/new.jinja2", form=form)
        categoria = SoporteCategoria(
            nombre=nombre,
            rol_id=form.rol.data,
            instrucciones=safe_message(form.instrucciones.data),
            departamento=form.departamento.data,
        )
        categoria.save()
        bitacora = Bitacora(
            modulo=Modulo.query.filter_by(nombre=MODULO).first(),
            usuario=current_user,
            descripcion=safe_message(f"Nuevo Soporte Categoría {categoria.nombre}"),
            url=url_for("soportes_categorias.detail", soporte_categoria_id=categoria.id),
        )
        bitacora.save()
        flash(bitacora.descripcion, "success")
        return redirect(bitacora.url)
    return render_template("soportes_categorias/new.jinja2", form=form)


@soportes_categorias.route("/soportes_categorias/edicion/<int:soporte_categoria_id>", methods=["GET", "POST"])
@permission_required(MODULO, Permiso.MODIFICAR)
def edit(soporte_categoria_id):
    """Editar Soporte Categoría"""
    categoria = SoporteCategoria.query.get_or_404(soporte_categoria_id)
    form = SoporteCategoriaForm()
    if form.validate_on_submit():
        es_valido = True
        # Si cambia el nombre, validar que el nombre no está en uso
        nombre = safe_string(form.nombre.data, save_enie=True)
        if categoria.nombre != nombre and SoporteCategoria.query.filter_by(nombre=nombre).first():
            flash("El nombre ya está en uso", "warning")
            es_valido = False
        # Si es válido
        if es_valido:
            # Guardar
            categoria.nombre = nombre
            categoria.rol_id = form.rol.data
            categoria.instrucciones = safe_message(form.instrucciones.data)
            categoria.departamento = form.departamento.data
            categoria.save()
            bitacora = Bitacora(
                modulo=Modulo.query.filter_by(nombre=MODULO).first(),
                usuario=current_user,
                descripcion=safe_message(f"Editado Soporte Categoría {categoria.nombre}"),
                url=url_for("soportes_categorias.detail", soporte_categoria_id=categoria.id),
            )
            bitacora.save()
            flash(bitacora.descripcion, "success")
            return redirect(bitacora.url)
    form.nombre.data = categoria.nombre
    form.rol.data = categoria.rol_id
    form.instrucciones.data = categoria.instrucciones
    form.departamento.data = categoria.departamento
    return render_template("soportes_categorias/edit.jinja2", form=form, categoria=categoria)


@soportes_categorias.route("/soportes_categorias/eliminar/<int:soporte_categoria_id>")
@permission_required(MODULO, Permiso.ADMINISTRAR)
def delete(soporte_categoria_id):
    """Eliminar Soporte Categoría"""
    categoria = SoporteCategoria.query.get_or_404(soporte_categoria_id)
    if categoria.estatus == "A":
        categoria.delete()
        bitacora = Bitacora(
            modulo=Modulo.query.filter_by(nombre=MODULO).first(),
            usuario=current_user,
            descripcion=safe_message(f"Eliminado Soporte Categoría {categoria.nombre}"),
            url=url_for("soportes_categorias.detail", soporte_categoria_id=categoria.id),
        )
        bitacora.save()
        flash(bitacora.descripcion, "success")
    return redirect(url_for("soportes_categorias.detail", soporte_categoria_id=categoria.id))


@soportes_categorias.route("/soportes_categorias/recuperar/<int:soporte_categoria_id>")
@permission_required(MODULO, Permiso.ADMINISTRAR)
def recover(soporte_categoria_id):
    """Recuperar Soporte Categoría"""
    categoria = SoporteCategoria.query.get_or_404(soporte_categoria_id)
    if categoria.estatus == "B":
        categoria.recover()
        bitacora = Bitacora(
            modulo=Modulo.query.filter_by(nombre=MODULO).first(),
            usuario=current_user,
            descripcion=safe_message(f"Recuperado Soporte Categoría {categoria.nombre}"),
            url=url_for("soportes_categorias.detail", soporte_categoria_id=categoria.id),
        )
        bitacora.save()
        flash(bitacora.descripcion, "success")
    return redirect(url_for("soportes_categorias.detail", soporte_categoria_id=categoria.id))
