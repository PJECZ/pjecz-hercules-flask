"""
Funcionarios, vistas
"""

import json

from flask import Blueprint, flash, redirect, render_template, request, url_for
from flask_login import current_user, login_required

from hercules.blueprints.bitacoras.models import Bitacora
from hercules.blueprints.funcionarios.models import Funcionario
from hercules.blueprints.modulos.models import Modulo
from hercules.blueprints.permisos.models import Permiso
from hercules.blueprints.usuarios.decorators import permission_required
from lib.datatables import get_datatable_parameters, output_datatable_json
from lib.safe_string import safe_curp, safe_email, safe_message, safe_string

MODULO = "FUNCIONARIOS"

funcionarios = Blueprint("funcionarios", __name__, template_folder="templates")


@funcionarios.before_request
@login_required
@permission_required(MODULO, Permiso.VER)
def before_request():
    """Permiso por defecto"""


@funcionarios.route("/funcionarios/datatable_json", methods=["GET", "POST"])
def datatable_json():
    """DataTable JSON para listado de Funcionarios"""
    # Tomar parámetros de Datatables
    draw, start, rows_per_page = get_datatable_parameters()
    # Consultar
    consulta = Funcionario.query
    # Primero filtrar por columnas propias
    if "estatus" in request.form:
        consulta = consulta.filter_by(estatus=request.form["estatus"])
    else:
        consulta = consulta.filter_by(estatus="A")
    if "centro_trabajo_id" in request.form:
        consulta = consulta.filter_by(centro_trabajo_id=request.form["centro_trabajo_id"])
    if "nombres" in request.form:
        nombres = safe_string(request.form["nombres"])
        if nombres != "":
            consulta = consulta.filter(Funcionario.nombres.contains(nombres))
    if "apellido_paterno" in request.form:
        apellido_paterno = safe_string(request.form["apellido_paterno"])
        if apellido_paterno != "":
            consulta = consulta.filter(Funcionario.apellido_paterno.contains(apellido_paterno))
    if "apellido_materno" in request.form:
        apellido_materno = safe_string(request.form["apellido_materno"])
        if apellido_materno != "":
            consulta = consulta.filter(Funcionario.apellido_materno.contains(apellido_materno))
    if "curp" in request.form:
        try:
            curp = safe_curp(request.form["curp"])
            if curp != "":
                consulta = consulta.filter(Funcionario.curp.contains(curp))
        except ValueError:
            pass
    if "puesto" in request.form:
        puesto = safe_string(request.form["puesto"])
        if puesto != "":
            consulta = consulta.filter(Funcionario.puesto.contains(puesto))
    if "email" in request.form:
        try:
            email = safe_email(request.form["email"], search_fragment=True)
            if email != "":
                consulta = consulta.filter(Funcionario.email.contains(email))
        except ValueError:
            pass
    if "en_funciones" in request.form and request.form["en_funciones"] == "true":
        consulta = consulta.filter(Funcionario.en_funciones is True)
    if "en_sentencias" in request.form and request.form["en_sentencias"] == "true":
        consulta = consulta.filter(Funcionario.en_sentencias is True)
    if "en_soportes" in request.form and request.form["en_soportes"] == "true":
        consulta = consulta.filter(Funcionario.en_soportes is True)
    if "en_tesis_jurisprudencias" in request.form and request.form["en_tesis_jurisprudencias"] == "true":
        consulta = consulta.filter(Funcionario.en_tesis_jurisprudencias is True)
    # Ordenar y paginar
    registros = consulta.order_by(Funcionario.id).offset(start).limit(rows_per_page).all()
    total = consulta.count()
    # Elaborar datos para DataTable
    data = []
    for resultado in registros:
        data.append(
            {
                "detalle": {
                    "email": resultado.email,
                    "url": url_for("funcionarios.detail", funcionario_id=resultado.id),
                },
                "nombre": resultado.nombre,
                "puesto": resultado.puesto,
                "centro_trabajo": {
                    "nombre": resultado.centro_trabajo.nombre,
                    "url": (
                        url_for("centros_trabajos.detail", centro_trabajo_id=resultado.centro_trabajo_id)
                        if current_user.can_view("CENTROS TRABAJOS")
                        else ""
                    ),
                },
                "telefono": resultado.telefono,
                "extension": resultado.extension,
            }
        )
    # Entregar JSON
    return output_datatable_json(draw, total, data)


@funcionarios.route("/funcionarios")
def list_active():
    """Listado de Funcionarios activos"""
    return render_template(
        "funcionarios/list.jinja2",
        filtros=json.dumps({"estatus": "A"}),
        titulo="Funcionarios",
        estatus="A",
    )


@funcionarios.route("/funcionarios/en_funciones")
@permission_required(MODULO, Permiso.ADMINISTRAR)
def list_active_en_funciones():
    """Listado de Funcionarios activos y en funciones"""
    return render_template(
        "funcionarios/list.jinja2",
        filtros=json.dumps({"estatus": "A", "en_funciones": True}),
        titulo="Funcionarios en funciones",
        estatus="A",
        current_page="en_funciones",
    )


@funcionarios.route("/funcionarios/en_sentencias")
@permission_required(MODULO, Permiso.ADMINISTRAR)
def list_active_en_sentencias():
    """Listado de Funcionarios activos y en sentencias"""
    return render_template(
        "funcionarios/list.jinja2",
        filtros=json.dumps({"estatus": "A", "en_sentencias": True}),
        titulo="Funcionarios en sentencias",
        estatus="A",
        current_page="en_sentencias",
    )


@funcionarios.route("/funcionarios/en_soportes")
@permission_required(MODULO, Permiso.ADMINISTRAR)
def list_active_en_soportes():
    """Listado de Funcionarios activos y en soportes"""
    return render_template(
        "funcionarios/list.jinja2",
        filtros=json.dumps({"estatus": "A", "en_soportes": True}),
        titulo="Funcionarios en soportes",
        estatus="A",
        current_page="en_soportes",
    )


@funcionarios.route("/funcionarios/en_tesis_jurisprudencias")
@permission_required(MODULO, Permiso.ADMINISTRAR)
def list_active_en_tesis_jurisprudencias():
    """Listado de Funcionarios activos y en tesis y jurisprudencias"""
    return render_template(
        "funcionarios/list.jinja2",
        filtros=json.dumps({"estatus": "A", "en_tesis_jurisprudencias": True}),
        titulo="Funcionarios en tesis y jurisprudencias",
        estatus="A",
        current_page="en_tesis_jurisprudencias",
    )


@funcionarios.route("/funcionarios/inactivos")
@permission_required(MODULO, Permiso.ADMINISTRAR)
def list_inactive():
    """Listado de Funcionarios inactivos"""
    return render_template(
        "funcionarios/list.jinja2",
        filtros=json.dumps({"estatus": "B"}),
        titulo="Funcionarios inactivos",
        estatus="B",
    )


@funcionarios.route("/funcionarios/<int:funcionario_id>")
def detail(funcionario_id):
    """Detalle de un Funcionario"""
    funcionario = Funcionario.query.get_or_404(funcionario_id)
    return render_template("funcionarios/detail.jinja2", funcionario=funcionario)


@funcionarios.route("/funcionarios/eliminar/<int:funcionario_id>")
@permission_required(MODULO, Permiso.ADMINISTRAR)
def delete(funcionario_id):
    """Eliminar Funcionario"""
    funcionario = Funcionario.query.get_or_404(funcionario_id)
    if funcionario.estatus == "A":
        funcionario.delete()
        bitacora = Bitacora(
            modulo=Modulo.query.filter_by(nombre=MODULO).first(),
            usuario=current_user,
            descripcion=safe_message(f"Eliminado Funcionario {funcionario.nombre}"),
            url=url_for("funcionarios.detail", funcionario_id=funcionario.id),
        )
        bitacora.save()
        flash(bitacora.descripcion, "success")
    return redirect(url_for("funcionarios.detail", funcionario_id=funcionario.id))


@funcionarios.route("/funcionarios/recuperar/<int:funcionario_id>")
@permission_required(MODULO, Permiso.ADMINISTRAR)
def recover(funcionario_id):
    """Recuperar Funcionario"""
    funcionario = Funcionario.query.get_or_404(funcionario_id)
    if funcionario.estatus == "B":
        funcionario.recover()
        bitacora = Bitacora(
            modulo=Modulo.query.filter_by(nombre=MODULO).first(),
            usuario=current_user,
            descripcion=safe_message(f"Recuperado Funcionario {funcionario.nombre}"),
            url=url_for("funcionarios.detail", funcionario_id=funcionario.id),
        )
        bitacora.save()
        flash(bitacora.descripcion, "success")
    return redirect(url_for("funcionarios.detail", funcionario_id=funcionario.id))
