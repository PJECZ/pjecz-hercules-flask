"""
Identidades Generos, vistas
"""

import json

from flask import Blueprint, flash, redirect, render_template, request, url_for
from flask_login import current_user, login_required

from hercules.blueprints.bitacoras.models import Bitacora
from hercules.blueprints.identidades_generos.forms import IdentidadGeneroForm
from hercules.blueprints.identidades_generos.models import IdentidadGenero
from hercules.blueprints.modulos.models import Modulo
from hercules.blueprints.permisos.models import Permiso
from hercules.blueprints.usuarios.decorators import permission_required
from lib.datatables import get_datatable_parameters, output_datatable_json
from lib.safe_string import safe_expediente, safe_message, safe_string

MODULO = "IDENTIDADES GENEROS"

identidades_generos = Blueprint("identidades_generos", __name__, template_folder="templates")


@identidades_generos.before_request
@login_required
@permission_required(MODULO, Permiso.VER)
def before_request():
    """Permiso por defecto"""


@identidades_generos.route("/identidades_generos/datatable_json", methods=["GET", "POST"])
def datatable_json():
    """DataTable JSON para listado de Identidad Genero"""
    # Tomar parámetros de Datatables
    draw, start, rows_per_page = get_datatable_parameters()
    # Consultar
    consulta = IdentidadGenero.query
    # Primero filtrar por columnas propias
    if "estatus" in request.form:
        consulta = consulta.filter_by(estatus=request.form["estatus"])
    else:
        consulta = consulta.filter_by(estatus="A")
    if "procedimiento" in request.form:
        try:
            procedimiento = safe_expediente(request.form["procedimiento"])
            consulta = consulta.filter(IdentidadGenero.procedimiento.contains(procedimiento))
        except (IndexError, ValueError):
            pass
    if "nombre_actual" in request.form:
        nombre_actual = safe_string(request.form["nombre_actual"])
        if nombre_actual != "":
            consulta = consulta.filter(IdentidadGenero.nombre_actual.contains(nombre_actual))
    if "nombre_anterior" in request.form:
        nombre_anterior = safe_string(request.form["nombre_anterior"])
        if nombre_anterior != "":
            consulta = consulta.filter(IdentidadGenero.nombre_anterior.contains(nombre_anterior))
    if "lugar_nacimiento" in request.form:
        lugar_nacimiento = safe_string(request.form["lugar_nacimiento"])
        if lugar_nacimiento != "":
            consulta = consulta.filter(IdentidadGenero.lugar_nacimiento.contains(lugar_nacimiento))
    # Ordenar y paginar
    registros = consulta.order_by(IdentidadGenero.nombre_actual).offset(start).limit(rows_per_page).all()
    total = consulta.count()
    # Elaborar datos para DataTable
    data = []
    for resultado in registros:
        data.append(
            {
                "detalle": {
                    "procedimiento": resultado.procedimiento,
                    "url": url_for("identidades_generos.detail", identidad_genero_id=resultado.id),
                },
                "nombre_actual": resultado.nombre_actual,
                "nombre_anterior": resultado.nombre_anterior,
                "fecha_nacimiento": resultado.fecha_nacimiento.strftime("%Y-%m-%d 00:00:00"),
                "lugar_nacimiento": resultado.lugar_nacimiento,
                "genero_anterior": resultado.genero_anterior,
                "genero_actual": resultado.genero_actual,
            }
        )
    # Entregar JSON
    return output_datatable_json(draw, total, data)


@identidades_generos.route("/identidades_generos")
def list_active():
    """Listado de Identidades Géneros activos"""
    return render_template(
        "identidades_generos/list.jinja2",
        filtros=json.dumps({"estatus": "A"}),
        titulo="Identidad de Género",
        estatus="A",
    )


@identidades_generos.route("/identidades_generos/inactivos")
@permission_required(MODULO, Permiso.ADMINISTRAR)
def list_inactive():
    """Listado de Identidaded Géneros inactivos"""
    return render_template(
        "identidades_generos/list.jinja2",
        filtros=json.dumps({"estatus": "B"}),
        titulo="Identidad de Género inactivos",
        estatus="B",
    )


@identidades_generos.route("/identidades_generos/<int:identidad_genero_id>")
def detail(identidad_genero_id):
    """Detalle de un Identidades Géneros"""
    identidad_genero = IdentidadGenero.query.get_or_404(identidad_genero_id)
    return render_template("identidades_generos/detail.jinja2", identidad_genero=identidad_genero)


@identidades_generos.route("/identidades_generos/nuevo", methods=["GET", "POST"])
@permission_required(MODULO, Permiso.CREAR)
def new():
    """Nuevo Identidad de Género"""
    form = IdentidadGeneroForm()
    if form.validate_on_submit():
        es_valido = True
        nombre_anterior = safe_string(form.nombre_anterior.data)
        if nombre_anterior == "":
            flash("No es válido el nombre anterior", "warning")
        nombre_actual = safe_string(form.nombre_actual.data)
        if nombre_actual == "":
            flash("No es válido el nombre actual.", "warning")
            es_valido = False
        try:
            procedimiento = safe_expediente(form.procedimiento.data)
        except (IndexError, ValueError):
            flash("No es válido el Procedimiento.", "warning")
            es_valido = False
        if es_valido:
            identidad_genero = IdentidadGenero(
                nombre_anterior=nombre_anterior,
                nombre_actual=nombre_actual,
                fecha_nacimiento=form.fecha_nacimiento.data,
                lugar_nacimiento=safe_string(form.lugar_nacimiento.data),
                genero_anterior=form.genero_anterior.data,
                genero_actual=form.genero_actual.data,
                nombre_padre=safe_string(form.nombre_padre.data),
                nombre_madre=safe_string(form.nombre_madre.data),
                procedimiento=procedimiento,
            )
            identidad_genero.save()
            bitacora = Bitacora(
                modulo=Modulo.query.filter_by(nombre=MODULO).first(),
                usuario=current_user,
                descripcion=safe_message(f"Nueva identidad de género {identidad_genero.procedimiento}"),
                url=url_for("identidades_generos.detail", identidad_genero_id=identidad_genero.id),
            )
            bitacora.save()
            flash(bitacora.descripcion, "success")
            return redirect(bitacora.url)
    return render_template("identidades_generos/new.jinja2", form=form)


@identidades_generos.route("/identidades_generos/edicion/<int:identidad_genero_id>", methods=["GET", "POST"])
@permission_required(MODULO, Permiso.MODIFICAR)
def edit(identidad_genero_id):
    """Editar Identidad de género"""
    identidad_genero = IdentidadGenero.query.get_or_404(identidad_genero_id)
    form = IdentidadGeneroForm()
    if form.validate_on_submit():
        es_valido = True
        nombre_anterior = safe_string(form.nombre_anterior.data)
        if nombre_anterior == "":
            flash("No es válido el nombre anterior.", "warning")
            es_valido = False
        nombre_actual = safe_string(form.nombre_actual.data)
        if nombre_actual == "":
            flash("No es válido el nombre actual.", "warning")
            es_valido = False
        try:
            procedimiento = safe_expediente(form.procedimiento.data)
        except (IndexError, ValueError):
            flash("No es válido el Procedimiento.", "warning")
            es_valido = False
        if es_valido:
            identidad_genero.nombre_anterior = nombre_anterior
            identidad_genero.nombre_actual = nombre_actual
            identidad_genero.fecha_nacimiento = form.fecha_nacimiento.data
            identidad_genero.lugar_nacimiento = safe_string(form.lugar_nacimiento.data)
            identidad_genero.genero_anterior = form.genero_anterior.data
            identidad_genero.genero_actual = form.genero_actual.data
            identidad_genero.nombre_padre = safe_string(form.nombre_padre.data)
            identidad_genero.nombre_madre = safe_string(form.nombre_madre.data)
            identidad_genero.procedimiento = procedimiento
            identidad_genero.save()
            bitacora = Bitacora(
                modulo=Modulo.query.filter_by(nombre=MODULO).first(),
                usuario=current_user,
                descripcion=safe_message(f"Editado identidad de género {identidad_genero.nombre_actual}"),
                url=url_for("identidades_generos.detail", identidad_genero_id=identidad_genero.id),
            )
            bitacora.save()
            flash(bitacora.descripcion, "success")
            return redirect(bitacora.url)
    form.nombre_anterior.data = identidad_genero.nombre_anterior
    form.nombre_actual.data = identidad_genero.nombre_actual
    form.fecha_nacimiento.data = identidad_genero.fecha_nacimiento
    form.lugar_nacimiento.data = identidad_genero.lugar_nacimiento
    form.genero_anterior.data = identidad_genero.genero_anterior
    form.genero_actual.data = identidad_genero.genero_actual
    form.nombre_padre.data = identidad_genero.nombre_padre
    form.nombre_madre.data = identidad_genero.nombre_madre
    form.procedimiento.data = identidad_genero.procedimiento
    return render_template("identidades_generos/edit.jinja2", form=form, identidad_genero=identidad_genero)


@identidades_generos.route("/identidades_generos/eliminar/<int:identidad_genero_id>")
@permission_required(MODULO, Permiso.ADMINISTRAR)
def delete(identidad_genero_id):
    """Eliminar Identidad de Género"""
    identidad_genero = IdentidadGenero.query.get_or_404(identidad_genero_id)
    if identidad_genero.estatus == "A":
        identidad_genero.delete()
        bitacora = Bitacora(
            modulo=Modulo.query.filter_by(nombre=MODULO).first(),
            usuario=current_user,
            descripcion=safe_message(f"Eliminado Identidad de Género {identidad_genero.nombre_actual}"),
            url=url_for("identidades_generos.detail", identidad_genero_id=identidad_genero.id),
        )
        bitacora.save()
        flash(bitacora.descripcion, "success")
    return redirect(url_for("identidades_generos.detail", identidad_genero_id=identidad_genero.id))


@identidades_generos.route("/identidades_generos/recuperar/<int:identidad_genero_id>")
@permission_required(MODULO, Permiso.ADMINISTRAR)
def recover(identidad_genero_id):
    """Recuperar Identidad de Género"""
    identidad_genero = IdentidadGenero.query.get_or_404(identidad_genero_id)
    if identidad_genero.estatus == "B":
        identidad_genero.recover()
        bitacora = Bitacora(
            modulo=Modulo.query.filter_by(nombre=MODULO).first(),
            usuario=current_user,
            descripcion=safe_message(f"Recuperado Identidad de Género {identidad_genero.nombre_actual}"),
            url=url_for("identidades_generos.detail", identidad_genero_id=identidad_genero.id),
        )
        bitacora.save()
        flash(bitacora.descripcion, "success")
    return redirect(url_for("identidades_generos.detail", identidad_genero_id=identidad_genero.id))
