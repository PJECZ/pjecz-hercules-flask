"""
Municipios, vistas
"""

import json
from flask import Blueprint, render_template, request, url_for
from flask_login import login_required

from lib.datatables import get_datatable_parameters, output_datatable_json
from lib.safe_string import safe_string

from hercules.blueprints.permisos.models import Permiso
from hercules.blueprints.usuarios.decorators import permission_required
from hercules.blueprints.municipios.models import Municipio

MODULO = "MUNICIPIOS"

municipios = Blueprint("municipios", __name__, template_folder="templates")


@municipios.before_request
@login_required
@permission_required(MODULO, Permiso.VER)
def before_request():
    """Permiso por defecto"""


@municipios.route("/municipios/datatable_json", methods=["GET", "POST"])
def datatable_json():
    """DataTable JSON para listado de Municipios"""
    # Tomar parámetros de Datatables
    draw, start, rows_per_page = get_datatable_parameters()
    # Consultar
    consulta = Municipio.query
    # Primero filtrar por columnas propias
    if "estatus" in request.form:
        consulta = consulta.filter_by(estatus=request.form["estatus"])
    else:
        consulta = consulta.filter_by(estatus="A")
    if "estado_id" in request.form:
        consulta = consulta.filter_by(estado_id=request.form["estado_id"])
    if "clave" in request.form:
        try:
            clave = str(int(request.form["clave"])).zfill(3)
            if clave != "":
                consulta = consulta.filter(Municipio.clave == clave)
        except ValueError:
            pass
    if "nombre" in request.form:
        nombre = safe_string(request.form["nombre"], save_enie=True)
        if nombre != "":
            consulta = consulta.filter(Municipio.nombre.contains(nombre))
    # Ordenar y paginar
    registros = consulta.order_by(Municipio.id).offset(start).limit(rows_per_page).all()
    total = consulta.count()
    # Elaborar datos para DataTable
    data = []
    for resultado in registros:
        data.append(
            {
                "estado_nombre": resultado.estado.nombre,
                "detalle": {
                    "clave": resultado.clave,
                    "url": url_for("municipios.detail", municipio_id=resultado.id),
                },
                "nombre": resultado.nombre,
            }
        )
    # Entregar JSON
    return output_datatable_json(draw, total, data)


@municipios.route("/municipios/select_json/<int:estado_id>", methods=["GET", "POST"])
def select_json(estado_id=None):
    """Select JSON para Municipios"""
    # Si estado_id es None, entonces no se entregan autoriades
    if estado_id is None:
        return json.dumps([])
    # Consultar
    consulta = Municipio.query.filter_by(estado_id=estado_id, estatus="A").order_by(Municipio.nombre)
    # Elaborar datos para Select
    data = []
    for resultado in consulta.all():
        data.append(
            {
                "id": resultado.id,
                "nombre": resultado.nombre,
            }
        )
    # Entregar JSON
    return json.dumps(data)


@municipios.route("/municipios")
def list_active():
    """Listado de Municipios activos"""
    return render_template(
        "municipios/list.jinja2",
        filtros=json.dumps({"estatus": "A"}),
        titulo="Municipios",
        estatus="A",
    )


@municipios.route("/municipios/<int:municipio_id>")
def detail(municipio_id):
    """Detalle de un Municipio"""
    municipio = Municipio.query.get_or_404(municipio_id)
    return render_template("municipios/detail.jinja2", municipio=municipio)
