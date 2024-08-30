"""
Nomimas Personas, vistas
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
from hercules.blueprints.nom_personas.models import NomPersona

MODULO = "NOM PERSONAS"

nom_personas = Blueprint("nom_personas", __name__, template_folder="templates")


@nom_personas.before_request
@login_required
@permission_required(MODULO, Permiso.VER)
def before_request():
    """Permiso por defecto"""


@nom_personas.route("/nom_personas/datatable_json", methods=["GET", "POST"])
def datatable_json():
    """DataTable JSON para listado de NomPersona"""
    # Tomar parámetros de Datatables
    draw, start, rows_per_page = get_datatable_parameters()
    # Consultar
    consulta = NomPersona.query
    # Primero filtrar por columnas propias
    if "estatus" in request.form:
        consulta = consulta.filter_by(estatus=request.form["estatus"])
    else:
        consulta = consulta.filter_by(estatus="A")
    # if "persona_id" in request.form:
    #     consulta = consulta.filter_by(persona_id=request.form["persona_id"])
    # Luego filtrar por columnas de otras tablas
    # if "persona_rfc" in request.form:
    #     consulta = consulta.join(Persona)
    #     consulta = consulta.filter(Persona.rfc.contains(safe_rfc(request.form["persona_rfc"], search_fragment=True)))
    # Ordenar y paginar
    registros = consulta.order_by(NomPersona.id).offset(start).limit(rows_per_page).all()
    total = consulta.count()
    # Elaborar datos para DataTable
    data = []
    for resultado in registros:
        data.append(
            {
                "rfc": resultado.rfc,
                "nombres": resultado.nombres,
                "apellido_primero": resultado.apellido_primero,
                "apellido_segundo": resultado.apellido_segundo,
                # "detalle": {
                #     "nombre": resultado.nombre,
                #     "url": url_for("nom_personas.detail", nom_persona_id=resultado.id),
                # },
            }
        )
    # Entregar JSON
    return output_datatable_json(draw, total, data)


@nom_personas.route("/nom_personas")
def list_active():
    """Listado de NomPersona activos"""
    return render_template(
        "nom_personas/list.jinja2",
        filtros=json.dumps({"estatus": "A"}),
        titulo="Nóminas Personas",
        estatus="A",
    )
