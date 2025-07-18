"""
Req Requisiciones, vistas
"""

import json
from flask import Blueprint, flash, redirect, render_template, request, url_for
from flask_login import current_user, login_required

from lib.datatables import get_datatable_parameters, output_datatable_json
from lib.safe_string import safe_string, safe_message, safe_clave
from sqlalchemy import or_

from hercules.blueprints.bitacoras.models import Bitacora
from hercules.blueprints.modulos.models import Modulo
from hercules.blueprints.permisos.models import Permiso
from hercules.blueprints.usuarios.decorators import permission_required
from hercules.blueprints.req_requisiciones.models import ReqRequisicion
from hercules.blueprints.usuarios.models import Usuario
from hercules.blueprints.autoridades.models import Autoridad


# Roles necesarios
ROL_LECTOR = "REQUISICIONES LECTOR"
ROL_ESCRITOR = "REQUISICIONES ESCRITOR"
ROL_SOLICITANTE = "REQUISICIONES SOLICITANTE"
ROL_AUTORIZANTE = "REQUISICIONES AUTORIZANTE"
ROL_REVISOR = "REQUISICIONES REVISOR"
ROL_MATERIALES = "REQUISICIONES MATERIALES"


MODULO = "REQ REQUISICIONES"

req_requisiciones = Blueprint("req_requisiciones", __name__, template_folder="templates")


@req_requisiciones.before_request
@login_required
@permission_required(MODULO, Permiso.VER)
def before_request():
    """Permiso por defecto"""


@req_requisiciones.route("/req_requisiciones/datatable_json", methods=["GET", "POST"])
def datatable_json():
    """DataTable JSON para listado de Req Requisiciones"""
    # Tomar parámetros de Datatables
    draw, start, rows_per_page = get_datatable_parameters()
    # Consultar
    consulta = ReqRequisicion.query
    # Primero filtrar por columnas propias
    if "estatus" in request.form:
        consulta = consulta.filter(ReqRequisicion.estatus == request.form["estatus"])
    else:
        consulta = consulta.filter(ReqRequisicion.estatus == "A")
    if "folio" in request.form:
        folio = safe_string(request.form["folio"])
        if folio:
            consulta = consulta.filter(ReqRequisicion.folio.contains(folio))
    if "justificacion" in request.form:
        justificacion = safe_string(request.form["justificacion"])
        if justificacion:
            consulta = consulta.filter(ReqRequisicion.justificacion.contains(justificacion))
    if "estado" in request.form:
        consulta = consulta.filter(ReqRequisicion.estado == request.form["estado"])
    # Filtrar por usuario id
    if "usuario_id" in request.form:
        consulta = consulta.filter(ReqRequisicion.usuario_id == request.form["usuario_id"])
    # Filtrar por ID de autoridad
    tabla_usuario_incluida = False
    if "autoridad_id" in request.form:
        autoridad_id = int(request.form["autoridad_id"])
        if autoridad_id:
            consulta = consulta.join(Usuario)
            tabla_usuario_incluida = True
            consulta = consulta.filter(Usuario.autoridad_id == autoridad_id)
    # Filtrar por clave de la autoridad
    elif "autoridad_clave" in request.form:
        autoridad_clave = safe_clave(request.form["autoridad_clave"])
        if autoridad_clave:
            consulta = consulta.join(Usuario)
            tabla_usuario_incluida = True
            consulta = consulta.join(Autoridad, Usuario.autoridad_id == Autoridad.id)
            consulta = consulta.filter(Autoridad.clave.contains(autoridad_clave))
    if "usuario_nombre" in request.form:
        usuario_nombre = safe_string(request.form["usuario_nombre"])
        if usuario_nombre:
            if not tabla_usuario_incluida:
                consulta = consulta.join(Usuario)
                tabla_usuario_incluida = True
            palabras = usuario_nombre.split()
            for palabra in palabras:
                consulta = consulta.filter(
                    or_(
                        Usuario.nombres.contains(palabra),
                        Usuario.apellido_paterno.contains(palabra),
                        Usuario.apellido_materno.contains(palabra),
                    )
                )
    # Ordenar y paginar
    registros = consulta.order_by(ReqRequisicion.creado.desc()).offset(start).limit(rows_per_page).all()
    total = consulta.count()
    # Elaborar datos para DataTable
    data = []
    for resultado in registros:
        # Icono en detalle
        icono_detalle = None
        if resultado.esta_archivado:
            icono_detalle = "ARCHIVADO"
        elif resultado.esta_cancelado:
            icono_detalle = "CANCELADO"
        # Elaborar registro
        data.append(
            {
                "detalle": {
                    "id": resultado.id,
                    "icono": icono_detalle,
                    "url": url_for("req_requisiciones.detail", req_requisicion_id=resultado.id),
                },
                "creado": resultado.creado.strftime("%Y-%m-%d %H:%M"),
                "usuario": resultado.usuario.nombre,
                "autoridad": {
                    "clave": resultado.usuario.autoridad.clave,
                    "nombre": resultado.usuario.autoridad.descripcion_corta,
                },
                "folio": resultado.folio,
                "justificacion": resultado.justificacion,
                "estado": resultado.estado,
            }
        )
    # Entregar JSON
    return output_datatable_json(draw, total, data)


@req_requisiciones.route("/req_requisiciones")
def list_active():
    """Listado de Req Requisiciones activos"""
    return render_template(
        "req_requisiciones/list.jinja2",
        filtros=json.dumps({"estatus": "A", "usuario_id": current_user.id}),
        titulo="Mis Requisiciones",
        estatus="A",
        estados=ReqRequisicion.ESTADOS,
        boton_activo="MIS REQUISICIONES",
    )


@req_requisiciones.route("/req_requisiciones_mi_autoridad")
def list_active_mi_autoridad():
    """Listado de Req Requisiciones de mi autoridad activos"""
    return render_template(
        "req_requisiciones/list.jinja2",
        filtros=json.dumps({"estatus": "A", "autoridad_id": current_user.autoridad.id}),
        titulo=f"Requisiciones de {current_user.autoridad.descripcion_corta}",
        estatus="A",
        estados=ReqRequisicion.ESTADOS,
        boton_activo="MI AUTORIDAD",
    )


@req_requisiciones.route("/req_requisiciones/inactivos")
@permission_required(MODULO, Permiso.ADMINISTRAR)
def list_inactive():
    """Listado de Req Requisiciones inactivos"""
    return render_template(
        "req_requisiciones/list.jinja2",
        filtros=json.dumps({"estatus": "B"}),
        titulo="Requisiciones inactivas",
        estatus="B",
        estados=ReqRequisicion.ESTADOS,
    )


@req_requisiciones.route("/req_requisiciones/<req_requisicion_id>")
def detail(req_requisicion_id):
    """Detalle de un Req Requisición"""
    req_requisicion = ReqRequisicion.query.get_or_404(req_requisicion_id)
    return render_template("req_requisiciones/detail.jinja2", req_requisicion=req_requisicion)


@req_requisiciones.route("/req_requisiciones/nuevo", methods=["GET", "POST"])
@permission_required(MODULO, Permiso.CREAR)
def new():
    """Nuevo Req Requisición"""
    return render_template("req_requisiciones/new.jinja2", form=form)
