"""
Listas de acuerdos, vistas
"""

import json
import re

from flask import Blueprint, flash, redirect, render_template, request, url_for
from flask_login import current_user, login_required
import pytz

from hercules.blueprints.bitacoras.models import Bitacora
from hercules.blueprints.modulos.models import Modulo
from hercules.blueprints.listas_de_acuerdos.models import ListaDeAcuerdo
from hercules.blueprints.permisos.models import Permiso
from hercules.blueprints.usuarios.decorators import permission_required
from lib.datatables import get_datatable_parameters, output_datatable_json
from lib.safe_string import safe_message, safe_string

TIMEZONE = "America/Mexico_City"
local_tz = pytz.timezone(TIMEZONE)

MODULO = "LISTAS DE ACUERDOS"

listas_de_acuerdos = Blueprint("listas_de_acuerdos", __name__, template_folder="templates")


@listas_de_acuerdos.before_request
@login_required
@permission_required(MODULO, Permiso.VER)
def before_request():
    """Permiso por defecto"""


@listas_de_acuerdos.route("/listas_de_acuerdos/datatable_json", methods=["GET", "POST"])
def datatable_json():
    """DataTable JSON para listado de ListaDeAcuerdo"""
    # Tomar parámetros de Datatables
    draw, start, rows_per_page = get_datatable_parameters()
    # Consultar
    consulta = ListaDeAcuerdo.query
    # Primero filtrar por columnas propias
    if "estatus" in request.form:
        consulta = consulta.filter_by(estatus=request.form["estatus"])
    else:
        consulta = consulta.filter_by(estatus="A")
    if "autoridad_id" in request.form:
        consulta = consulta.filter_by(autoridad_id=request.form["autoridad_id"])
    # Ordenar y paginar
    registros = consulta.order_by(ListaDeAcuerdo.id.desc()).offset(start).limit(rows_per_page).all()
    total = consulta.count()
    # Elaborar datos para DataTable
    data = []
    for lista_de_acuerdo in registros:
        # La columna creado esta en UTC, convertir a local
        creado_local = lista_de_acuerdo.creado.astimezone(local_tz)
        # Por defecto el semaforo es verde (0)
        semaforo = 0
        # Acumular datos
        data.append(
            {
                "detalle": {
                    "fecha": lista_de_acuerdo.fecha.strftime("%Y-%m-%d"),
                    "url": url_for("listas_de_acuerdos.detail", lista_de_acuerdo_id=lista_de_acuerdo.id),
                },
                "descripcion": lista_de_acuerdo.descripcion,
                "creado": {
                    "tiempo": creado_local.strftime("%Y-%m-%d %H:%M"),
                    "semaforo": semaforo,
                },
            }
        )
    # Entregar JSON
    return output_datatable_json(draw, total, data)


@listas_de_acuerdos.route("/listas_de_acuerdos/admin_datatable_json", methods=["GET", "POST"])
def admin_datatable_json():
    """DataTable JSON para listado admin de ListaDeAcuerdo"""
    # Tomar parámetros de Datatables
    draw, start, rows_per_page = get_datatable_parameters()
    # Consultar
    consulta = ListaDeAcuerdo.query
    # Primero filtrar por columnas propias
    if "estatus" in request.form:
        consulta = consulta.filter(ListaDeAcuerdo.estatus == request.form["estatus"])
    else:
        consulta = consulta.filter(estatus="A")
    if "autoridad_id" in request.form:
        consulta = consulta.filter(ListaDeAcuerdo.autoridad_id == request.form["autoridad_id"])
    fecha_desde = None
    fecha_hasta = None
    if "fecha_desde" in request.form and re.match(r"\d{4}-\d{2}-\d{2}", request.form["fecha_desde"]):
        fecha_desde = request.form["fecha_desde"]
    if "fecha_hasta" in request.form and re.match(r"\d{4}-\d{2}-\d{2}", request.form["fecha_hasta"]):
        fecha_hasta = request.form["fecha_hasta"]
    if fecha_desde and fecha_hasta and fecha_desde > fecha_hasta:
        fecha_desde, fecha_hasta = fecha_hasta, fecha_desde
    if fecha_desde:
        consulta = consulta.filter(ListaDeAcuerdo.fecha >= fecha_desde)
    if fecha_hasta:
        consulta = consulta.filter(ListaDeAcuerdo.fecha <= fecha_hasta)
    # Ordenar y paginar
    registros = consulta.order_by(ListaDeAcuerdo.id.desc()).offset(start).limit(rows_per_page).all()
    total = consulta.count()
    # Elaborar datos para DataTable
    data = []
    for lista_de_acuerdo in registros:
        # La columna creado esta en UTC, convertir a local
        creado_local = lista_de_acuerdo.creado.astimezone(local_tz)
        # Por defecto el semaforo es verde (0)
        semaforo = 0
        # Acumular datos
        data.append(
            {
                "detalle": {
                    "id": lista_de_acuerdo.id,
                    "url": url_for("listas_de_acuerdos.detail", lista_de_acuerdo_id=lista_de_acuerdo.id),
                },
                "creado": {
                    "tiempo": creado_local.strftime("%Y-%m-%d %H:%M"),
                    "semaforo": semaforo,
                },
                "autoridad_clave": lista_de_acuerdo.autoridad.clave,
                "fecha": lista_de_acuerdo.fecha.strftime("%Y-%m-%d"),
                "descripcion": lista_de_acuerdo.descripcion,
            }
        )
    # Entregar JSON
    return output_datatable_json(draw, total, data)


@listas_de_acuerdos.route("/listas_de_acuerdos")
def list_active():
    """Listado de ListaDeAcuerdo activos"""
    # Si es administrador ve todas las listas de acuerdos
    if current_user.can_admin("LISTAS DE ACUERDOS"):
        return render_template(
            "listas_de_acuerdos/list_admin.jinja2",
            filtros=json.dumps({"estatus": "A"}),
            titulo="Todas las listas de Acuerdos",
            estatus="A",
        )
    # Si es jurisdiccional ve lo de su autoridad
    if current_user.autoridad.es_jurisdiccional:
        autoridad = current_user.autoridad
        return render_template(
            "listas_de_acuerdos/list.jinja2",
            filtros=json.dumps({"autoridad_id": autoridad.id, "estatus": "A"}),
            titulo=f"Listas de Acuerdos de {autoridad.distrito.nombre_corto}, {autoridad.descripcion_corta}",
            estatus="A",
        )
    # Ninguno de los anteriores, es solo observador
    return render_template(
        "listas_de_acuerdos/list.jinja2",
        filtros=json.dumps({"estatus": "A"}),
        titulo="Listas de Acuerdos (observador)",
        estatus="A",
    )


@listas_de_acuerdos.route("/listas_de_acuerdos/inactivos")
@permission_required(MODULO, Permiso.ADMINISTRAR)
def list_inactive():
    """Listado de ListaDeAcuerdo inactivas"""
    # Solo los administradores ven todas las listas de acuerdos inactivas
    return render_template(
        "listas_de_acuerdos/list_admin.jinja2",
        filtros=json.dumps({"estatus": "B"}),
        titulo="Todas las listas de Acuerdos inactivas",
        estatus="B",
    )


@listas_de_acuerdos.route("/listas_de_acuerdos/<int:lista_de_acuerdo_id>")
def detail(lista_de_acuerdo_id):
    """Detalle de una ListaDeAcuerdo"""
    lista_de_acuerdo = ListaDeAcuerdo.query.get_or_404(lista_de_acuerdo_id)
    return render_template("listas_de_acuerdos/detail.jinja2", lista_de_acuerdo=lista_de_acuerdo)
