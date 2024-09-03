"""
Autoridades Funcionarios, vistas
"""

import json

from flask import Blueprint, flash, redirect, render_template, request, url_for
from flask_login import current_user, login_required

from hercules.blueprints.autoridades.models import Autoridad
from hercules.blueprints.autoridades_funcionarios.models import AutoridadFuncionario
from hercules.blueprints.bitacoras.models import Bitacora
from hercules.blueprints.funcionarios.models import Funcionario
from hercules.blueprints.modulos.models import Modulo
from hercules.blueprints.permisos.models import Permiso
from hercules.blueprints.usuarios.decorators import permission_required
from lib.datatables import get_datatable_parameters, output_datatable_json
from lib.safe_string import safe_clave, safe_message, safe_string

MODULO = "AUTORIDADES FUNCIONARIOS"

autoridades_funcionarios = Blueprint("autoridades_funcionarios", __name__, template_folder="templates")


@autoridades_funcionarios.before_request
@login_required
@permission_required(MODULO, Permiso.VER)
def before_request():
    """Permiso por defecto"""


@autoridades_funcionarios.route("/autoridades_funcionarios/datatable_json", methods=["GET", "POST"])
def datatable_json():
    """DataTable JSON para listado de Autoridades Funcionarios"""
    # Tomar parámetros de Datatables
    draw, start, rows_per_page = get_datatable_parameters()
    # Consultar
    consulta = AutoridadFuncionario.query
    # Primero filtrar por columnas propias
    if "estatus" in request.form:
        consulta = consulta.filter_by(estatus=request.form["estatus"])
    else:
        consulta = consulta.filter_by(estatus="A")
    if "autoridad_id" in request.form:
        autoridad = Autoridad.query.get(request.form["autoridad_id"])
        if autoridad:
            consulta = consulta.filter(AutoridadFuncionario.autoridad_id == autoridad.id)
    if "autoridad_clave" in request.form:
        try:
            autoridad_clave = safe_clave(request.form["autoridad_clave"])
            if autoridad_clave != "":
                consulta = consulta.join(Autoridad).filter(Autoridad.clave.contains(autoridad_clave))
        except ValueError:
            pass
    if "funcionario_id" in request.form:
        consulta = consulta.filter(AutoridadFuncionario.funcionario_id == request.form["funcionario_id"])
    if "funcionario_nombre" in request.form:
        funcionario_nombre = safe_string(request.form["funcionario_nombre"], save_enie=True)
        if funcionario_nombre != "":
            consulta = consulta.join(Funcionario).filter(Funcionario.nombres.contains(funcionario_nombre))
    if "autoridad_descripcion" in request.form:
        autoridad_descripcion = safe_string(request.form["autoridad_descripcion"], save_enie=True)
        if autoridad_descripcion != "":
            consulta = consulta.join(Autoridad).filter(Autoridad.descripcion_corta.contains(autoridad_descripcion))
    # Ordenar y paginar
    registros = consulta.order_by(AutoridadFuncionario.id).offset(start).limit(rows_per_page).all()
    total = consulta.count()
    # Elaborar datos para DataTable
    data = []
    for resultado in registros:
        data.append(
            {
                "detalle": {
                    "id": resultado.id,
                    "url": url_for("autoridades_funcionarios.detail", autoridad_funcionario_id=resultado.id),
                },
                "autoridad": {
                    "clave": resultado.autoridad.clave,
                    "url": (
                        url_for("autoridades.detail", autoridad_id=resultado.autoridad_id)
                        if current_user.can_view("AUTORIDADES")
                        else ""
                    ),
                },
                "autoridad_descripcion_corta": resultado.autoridad.descripcion_corta,
                "funcionario": {
                    "curp": resultado.funcionario.curp,
                    "url": (
                        url_for("funcionarios.detail", funcionario_id=resultado.funcionario_id)
                        if current_user.can_view("FUNCIONARIOS")
                        else ""
                    ),
                },
                "funcionario_nombre": resultado.funcionario.nombre,
            }
        )
    # Entregar JSON
    return output_datatable_json(draw, total, data)


@autoridades_funcionarios.route("/autoridades_funcionarios")
def list_active():
    """Listado de Autoridades Funcionarios activos"""
    return render_template(
        "autoridades_funcionarios/list.jinja2",
        filtros=json.dumps({"estatus": "A"}),
        titulo="Autoridades Funcionarios",
        estatus="A",
    )


@autoridades_funcionarios.route("/autoridades_funcionarios/inactivos")
@permission_required(MODULO, Permiso.ADMINISTRAR)
def list_inactive():
    """Listado de Autoridades Funcionarios inactivos"""
    return render_template(
        "autoridades_funcionarios/list.jinja2",
        filtros=json.dumps({"estatus": "B"}),
        titulo="Autoridades Funcionarios inactivos",
        estatus="B",
    )


@autoridades_funcionarios.route("/autoridades_funcionarios/<int:autoridad_funcionario_id>")
def detail(autoridad_funcionario_id):
    """Detalle de un Autoridad Funcionario"""
    autoridad_funcionario = AutoridadFuncionario.query.get_or_404(autoridad_funcionario_id)
    return render_template("autoridades_funcionarios/detail.jinja2", autoridad_funcionario=autoridad_funcionario)


@autoridades_funcionarios.route("/autoridades_funcionarios/eliminar/<int:autoridad_funcionario_id>")
@permission_required(MODULO, Permiso.ADMINISTRAR)
def delete(autoridad_funcionario_id):
    """Eliminar Autoridad-Funcionario"""
    autoridad_funcionario = AutoridadFuncionario.query.get_or_404(autoridad_funcionario_id)
    if autoridad_funcionario.estatus == "A":
        autoridad_funcionario.delete()
        bitacora = Bitacora(
            modulo=Modulo.query.filter_by(nombre=MODULO).first(),
            usuario=current_user,
            descripcion=safe_message(f"Eliminado Autoridad-Funcionario {autoridad_funcionario.descripcion}"),
            url=url_for("autoridades_funcionarios.detail", autoridad_funcionario_id=autoridad_funcionario.id),
        )
        bitacora.save()
        flash(bitacora.descripcion, "success")
    return redirect(url_for("autoridades_funcionarios.detail", autoridad_funcionario_id=autoridad_funcionario.id))


@autoridades_funcionarios.route("/autoridades_funcionarios/recuperar/<int:autoridad_funcionario_id>")
@permission_required(MODULO, Permiso.ADMINISTRAR)
def recover(autoridad_funcionario_id):
    """Recuperar Autoridad-Funcionario"""
    autoridad_funcionario = AutoridadFuncionario.query.get_or_404(autoridad_funcionario_id)
    if autoridad_funcionario.estatus == "B":
        autoridad_funcionario.recover()
        bitacora = Bitacora(
            modulo=Modulo.query.filter_by(nombre=MODULO).first(),
            usuario=current_user,
            descripcion=safe_message(f"Recuperado Autoridad-Funcionario {autoridad_funcionario.descripcion}"),
            url=url_for("autoridades_funcionarios.detail", autoridad_funcionario_id=autoridad_funcionario.id),
        )
        bitacora.save()
        flash(bitacora.descripcion, "success")
    return redirect(url_for("autoridades_funcionarios.detail", autoridad_funcionario_id=autoridad_funcionario.id))
