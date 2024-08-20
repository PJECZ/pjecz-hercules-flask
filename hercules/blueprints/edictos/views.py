"""
Edictos, vistas
"""

import json

from flask import Blueprint, flash, redirect, render_template, request, url_for
from flask_login import current_user, login_required

from hercules.blueprints.autoridades.models import Autoridad
from hercules.blueprints.bitacoras.models import Bitacora
from hercules.blueprints.edictos.models import Edicto
from hercules.blueprints.modulos.models import Modulo
from hercules.blueprints.permisos.models import Permiso
from hercules.blueprints.usuarios.decorators import permission_required
from lib.datatables import get_datatable_parameters, output_datatable_json
from lib.safe_string import safe_expediente, safe_message, safe_numero_publicacion, safe_string

MODULO = "EDICTOS"

edictos = Blueprint("edictos", __name__, template_folder="templates")


@edictos.before_request
@login_required
@permission_required(MODULO, Permiso.VER)
def before_request():
    """Permiso por defecto"""


@edictos.route("/edictos/datatable_json", methods=["GET", "POST"])
def datatable_json():
    """DataTable JSON para listado de Edictos"""
    # Tomar parámetros de Datatables
    draw, start, rows_per_page = get_datatable_parameters()
    # Consultar
    consulta = Edicto.query
    # Primero filtrar por columnas propias
    if "estatus" in request.form:
        consulta = consulta.filter_by(estatus=request.form["estatus"])
    else:
        consulta = consulta.filter_by(estatus="A")
    if "autoridad_id" in request.form:
        autoridad = Autoridad.query.get(request.form["autordiad_id"])
        if autoridad:
            consulta = consulta.filter_by(autoridad=autoridad)
    if "fecha_desde" in request.form:
        consulta = consulta.filter(Edicto.fecha >= request.form["fecha_desde"])
    if "fecha_hasta" in request.form:
        consulta = consulta.filter(Edicto.fecha <= request.form["fecha_hasta"])
    if "descripcion" in request.form:
        consulta = consulta.filter(Edicto.descripcion.contains(safe_string(request.form["descripcion"])))
    if "expediente" in request.form:
        try:
            expediente = safe_expediente(request.form["expediente"])
            consulta = consulta.filter_by(expediente=expediente)
        except (IndexError, ValueError):
            pass
    if "numero_publicacion" in request.form:
        try:
            numero_publicacion = safe_numero_publicacion(request.form["numero_publicacion"])
            consulta = consulta.filter_by(numero_publicacion=numero_publicacion)
        except (IndexError, ValueError):
            pass
    # Ordenar y paginar
    registros = consulta.order_by(Edicto.fecha.desc()).offset(start).limit(rows_per_page).all()
    total = consulta.count()
    # Elaborar datos para DataTable
    data = []
    for resultado in registros:
        data.append(
            {
                "fecha": resultado.fecha.strftime("%Y-%m-%d 00:00:00"),
                "detalle": {
                    "descripcion": resultado.descripcion,
                    "url": url_for("edictos.detail", edicto_id=resultado.id),
                },
                "expediente": resultado.expediente,
                "numero_publicacion": resultado.numero_publicacion,
            }
        )
    # Entregar JSON
    return output_datatable_json(draw, total, data)


@edictos.route("/edictos")
def list_active():
    """Listado de Edictos activos"""
    return render_template(
        "edictos/list.jinja2",
        filtros=json.dumps({"estatus": "A"}),
        titulo="Edictos",
        estatus="A",
    )


@edictos.route("/edictos/inactivos")
@permission_required(MODULO, Permiso.ADMINISTRAR)
def list_inactive():
    """Listado de Edictos inactivos"""
    return render_template(
        "edictos/list.jinja2",
        filtros=json.dumps({"estatus": "B"}),
        titulo="Edictos inactivos",
        estatus="B",
    )


@edictos.route("/edictos/<int:edicto_id>")
def detail(edicto_id):
    """Detalle de un Edicto"""
    edicto = Edicto.query.get_or_404(edicto_id)
    return render_template("edictos/detail.jinja2", edicto=edicto)


@edictos.route("/edictos/eliminar/<int:edicto_id>")
@permission_required(MODULO, Permiso.ADMINISTRAR)
def delete(edicto_id):
    """Eliminar Edicto"""
    edicto = Edicto.query.get_or_404(edicto_id)
    if edicto.estatus == "A":
        edicto.delete()
        bitacora = Bitacora(
            modulo=Modulo.query.filter_by(nombre=MODULO).first(),
            usuario=current_user,
            descripcion=safe_message(f"Eliminado Edicto {edicto.descripcion}"),
            url=url_for("edictos.detail", edicto_id=edicto.id),
        )
        bitacora.save()
        flash(bitacora.descripcion, "success")
    return redirect(url_for("edictos.detail", edicto_id=edicto.id))


@edictos.route("/edictos/recuperar/<int:edicto_id>")
@permission_required(MODULO, Permiso.ADMINISTRAR)
def recover(edicto_id):
    """Recuperar Edicto"""
    edicto = Edicto.query.get_or_404(edicto_id)
    if edicto.estatus == "B":
        edicto.recover()
        bitacora = Bitacora(
            modulo=Modulo.query.filter_by(nombre=MODULO).first(),
            usuario=current_user,
            descripcion=safe_message(f"Recuperado Edicto {edicto.descripcion}"),
            url=url_for("edictos.detail", edicto_id=edicto.id),
        )
        bitacora.save()
        flash(bitacora.descripcion, "success")
    return redirect(url_for("edictos.detail", edicto_id=edicto.id))
