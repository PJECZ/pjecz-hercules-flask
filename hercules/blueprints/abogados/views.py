"""
Abogados, vistas
"""

import json

from flask import Blueprint, flash, redirect, render_template, request, url_for
from flask_login import current_user, login_required

from hercules.blueprints.abogados.forms import AbogadoForm
from hercules.blueprints.abogados.models import Abogado
from hercules.blueprints.bitacoras.models import Bitacora
from hercules.blueprints.modulos.models import Modulo
from hercules.blueprints.permisos.models import Permiso
from hercules.blueprints.usuarios.decorators import permission_required
from lib.datatables import get_datatable_parameters, output_datatable_json
from lib.safe_string import safe_message, safe_string

MODULO = "ABOGADOS"

abogados = Blueprint("abogados", __name__, template_folder="templates")


@abogados.before_request
@login_required
@permission_required(MODULO, Permiso.VER)
def before_request():
    """Permiso por defecto"""


@abogados.route("/abogados/datatable_json", methods=["GET", "POST"])
def datatable_json():
    """DataTable JSON para listado de abogados"""
    # Tomar parámetros de Datatables
    draw, start, rows_per_page = get_datatable_parameters()
    # Consultar
    consulta = Abogado.query
    if "estatus" in request.form:
        consulta = consulta.filter_by(estatus=request.form["estatus"])
    else:
        consulta = consulta.filter_by(estatus="A")
    if "fecha_desde" in request.form:
        consulta = consulta.filter(Abogado.fecha >= request.form["fecha_desde"])
    if "fecha_hasta" in request.form:
        consulta = consulta.filter(Abogado.fecha <= request.form["fecha_hasta"])
    if "numero" in request.form:
        consulta = consulta.filter_by(numero=safe_string(request.form["numero"]))
    if "libro" in request.form:
        consulta = consulta.filter_by(libro=safe_string(request.form["libro"]))
    if "nombre" in request.form:
        consulta = consulta.filter(Abogado.nombre.contains(safe_string(request.form["nombre"])))
    registros = consulta.order_by(Abogado.id.desc()).offset(start).limit(rows_per_page).all()
    total = consulta.count()
    # Elaborar datos para DataTable
    data = []
    for abogado in registros:
        data.append(
            {
                "detalle": {
                    "nombre": abogado.nombre,
                    "url": url_for("abogados.detail", abogado_id=abogado.id),
                },
                "fecha": abogado.fecha.strftime("%Y-%m-%d 00:00:00"),
                "numero": abogado.numero,
                "libro": abogado.libro,
            }
        )
    # Entregar JSON
    return output_datatable_json(draw, total, data)


@abogados.route("/abogados")
def list_active():
    """Listado de Abogados activos"""
    return render_template(
        "abogados/list.jinja2",
        filtros=json.dumps({"estatus": "A"}),
        titulo="Abogados registrados",
        estatus="A",
    )


@abogados.route("/abogados/inactivos")
@permission_required(MODULO, Permiso.MODIFICAR)
def list_inactive():
    """Listado de Abogados inactivos"""
    return render_template(
        "abogados/list.jinja2",
        filtros=json.dumps({"estatus": "B"}),
        titulo="Abogados registrados inactivos",
        estatus="B",
    )


@abogados.route("/abogados/<int:abogado_id>")
def detail(abogado_id):
    """Detalle de un Abogado"""
    abogado = Abogado.query.get_or_404(abogado_id)
    return render_template("abogados/detail.jinja2", abogado=abogado)


@abogados.route("/abogados/nuevo", methods=["GET", "POST"])
@permission_required(MODULO, Permiso.CREAR)
def new():
    """Nuevo Abogado"""
    form = AbogadoForm()
    if form.validate_on_submit():
        abogado = Abogado(
            numero=safe_string(form.numero.data),
            nombre=safe_string(form.nombre.data, save_enie=True),
            libro=safe_string(form.libro.data),
            fecha=form.fecha.data,
        )
        abogado.save()
        bitacora = Bitacora(
            modulo=Modulo.query.filter_by(nombre=MODULO).first(),
            usuario=current_user,
            descripcion=safe_message(f"Nuevo abogado registrado {abogado.nombre} con número {abogado.numero}"),
            url=url_for("abogados.detail", abogado_id=abogado.id),
        )
        bitacora.save()
        flash(bitacora.descripcion, "success")
        return redirect(bitacora.url)
    return render_template("abogados/new.jinja2", form=form)


@abogados.route("/abogados/edicion/<int:abogado_id>", methods=["GET", "POST"])
@permission_required(MODULO, Permiso.MODIFICAR)
def edit(abogado_id):
    """Editar Abogado"""
    abogado = Abogado.query.get_or_404(abogado_id)
    form = AbogadoForm()
    if form.validate_on_submit():
        abogado.numero = safe_string(form.numero.data)
        abogado.nombre = safe_string(form.nombre.data, save_enie=True)
        abogado.libro = safe_string(form.libro.data)
        abogado.fecha = form.fecha.data
        abogado.save()
        bitacora = Bitacora(
            modulo=Modulo.query.filter_by(nombre=MODULO).first(),
            usuario=current_user,
            descripcion=safe_message(f"Editado abogado registrado {abogado.nombre}"),
            url=url_for("abogados.detail", abogado_id=abogado.id),
        )
        bitacora.save()
        flash(bitacora.descripcion, "success")
        return redirect(bitacora.url)
    form.numero.data = abogado.numero
    form.nombre.data = abogado.nombre
    form.libro.data = abogado.libro
    form.fecha.data = abogado.fecha
    return render_template("abogados/edit.jinja2", form=form, abogado=abogado)


@abogados.route("/abogados/eliminar/<int:abogado_id>")
@permission_required(MODULO, Permiso.MODIFICAR)
def delete(abogado_id):
    """Eliminar Abogado"""
    abogado = Abogado.query.get_or_404(abogado_id)
    if abogado.estatus == "A":
        abogado.delete()
        bitacora = Bitacora(
            modulo=Modulo.query.filter_by(nombre=MODULO).first(),
            usuario=current_user,
            descripcion=safe_message(f"Eliminado abogado registrado {abogado.nombre}"),
            url=url_for("abogados.detail", abogado_id=abogado.id),
        )
        bitacora.save()
        flash(bitacora.descripcion, "success")
    return redirect(url_for("abogados.detail", abogado_id=abogado_id))


@abogados.route("/abogados/recuperar/<int:abogado_id>")
@permission_required(MODULO, Permiso.MODIFICAR)
def recover(abogado_id):
    """Recuperar Abogado"""
    abogado = Abogado.query.get_or_404(abogado_id)
    if abogado.estatus == "B":
        abogado.recover()
        bitacora = Bitacora(
            modulo=Modulo.query.filter_by(nombre=MODULO).first(),
            usuario=current_user,
            descripcion=safe_message(f"Recuperado abogado registrado {abogado.nombre}"),
            url=url_for("abogados.detail", abogado_id=abogado.id),
        )
        bitacora.save()
        flash(bitacora.descripcion, "success")
    return redirect(url_for("abogados.detail", abogado_id=abogado_id))
