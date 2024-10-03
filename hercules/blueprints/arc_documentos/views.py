"""
Archivo - Documentos, vistas
"""

import json
from flask import Blueprint, flash, redirect, render_template, request, url_for
from flask_login import current_user, login_required
from datetime import date
from dotenv import load_dotenv
from sqlalchemy import or_

from lib.datatables import get_datatable_parameters, output_datatable_json
from lib.safe_string import safe_string, safe_message, safe_expediente

from hercules.blueprints.bitacoras.models import Bitacora
from hercules.blueprints.modulos.models import Modulo
from hercules.blueprints.permisos.models import Permiso
from hercules.blueprints.usuarios.decorators import permission_required
from hercules.blueprints.arc_documentos.models import ArcDocumento
from hercules.blueprints.autoridades.models import Autoridad
from hercules.blueprints.arc_documentos_bitacoras.models import ArcDocumentoBitacora

from hercules.blueprints.arc_archivos.views import (
    ROL_JEFE_REMESA_ADMINISTRADOR,
    ROL_JEFE_REMESA,
    ROL_ARCHIVISTA,
    ROL_SOLICITANTE,
    ROL_LEVANTAMENTISTA,
)

MODULO = "ARC DOCUMENTOS"

arc_documentos = Blueprint("arc_documentos", __name__, template_folder="templates")


@arc_documentos.before_request
@login_required
@permission_required(MODULO, Permiso.VER)
def before_request():
    """Permiso por defecto"""


@arc_documentos.route("/arc_documentos/datatable_json", methods=["GET", "POST"])
def datatable_json():
    """DataTable JSON para listado de Documentos"""
    # Tomar parámetros de Datatables
    draw, start, rows_per_page = get_datatable_parameters()
    # Consultar
    consulta = ArcDocumento.query
    # Primero filtrar por columnas propias
    if "estatus" in request.form:
        consulta = consulta.filter(ArcDocumento.estatus == request.form["estatus"])
    else:
        consulta = consulta.filter(ArcDocumento.estatus == "A")
    if "expediente" in request.form:
        if request.form["expediente"].isnumeric():
            consulta = consulta.filter(ArcDocumento.expediente.contains(request.form["expediente"]))
        else:
            consulta = consulta.filter_by(expediente=safe_expediente(request.form["expediente"]))
    if "juicio" in request.form:
        juicio = safe_string(request.form["juicio"], save_enie=True)
        consulta = consulta.filter(ArcDocumento.juicio.contains(juicio))
    if "partes" in request.form:
        consulta = consulta.filter(
            or_(
                ArcDocumento.actor.contains(safe_string(request.form["partes"], save_enie=True)),
                ArcDocumento.demandado.contains(safe_string(request.form["partes"], save_enie=True)),
            )
        )
    if "tipo" in request.form:
        consulta = consulta.filter_by(arc_documento_tipo_id=int(request.form["tipo"]))
    if "ubicacion" in request.form:
        consulta = consulta.filter_by(ubicacion=request.form["ubicacion"])
    if "juzgado_id" in request.form:
        consulta = consulta.filter_by(autoridad_id=int(request.form["juzgado_id"]))
    if "juzgado_extinto_id" in request.form:
        consulta = consulta.filter_by(arc_juzgado_origen_id=int(request.form["juzgado_extinto_id"]))
    if "juzgado_extinto_clave" in request.form:
        consulta = consulta.filter(ArcDocumento.arc_juzgados_origen_claves.contains(request.form["juzgado_extinto_clave"]))
    # Luego filtrar por columnas de otras tablas
    if "distrito_id" in request.form:
        distrito_id = int(request.form["distrito_id"])
        consulta = consulta.join(Autoridad)
        consulta = consulta.filter(Autoridad.distrito_id == distrito_id)
    if "sede" in request.form:
        consulta = consulta.join(Autoridad)
        consulta = consulta.filter(Autoridad.sede == request.form["sede"])
    # Definir un set con los campos
    set_campos = {"expediente", "juicio", "partes", "tipo", "ubicacion", "juzgado_extinto_id", "distrito_id", "sede"}
    # Si se filtra por cualquiera de los campos mencionado, el orden es por número de expediente
    if set_campos.intersection(request.form):
        registros = (
            consulta.order_by(ArcDocumento.anio)
            .order_by(ArcDocumento.expediente_numero)
            .offset(start)
            .limit(rows_per_page)
            .all()
        )
    # De lo contrario, se ordena por creación.
    else:
        registros = consulta.order_by(ArcDocumento.creado.desc()).offset(start).limit(rows_per_page).all()
    total = consulta.count()
    # Elaborar datos para DataTable
    data = []
    for resultado in registros:
        data.append(
            {
                "expediente": {
                    "expediente": resultado.expediente,
                    "url": url_for("arc_documentos.detail", documento_id=resultado.id),
                },
                "juzgado": {
                    "clave": resultado.autoridad.clave,
                    "nombre": resultado.autoridad.descripcion_corta,
                    "url": (
                        url_for("autoridades.detail", autoridad_id=resultado.autoridad.id)
                        if current_user.can_view("AUTORIDADES")
                        else ""
                    ),
                },
                "juzgado_y_origen": {
                    "clave_actual": resultado.autoridad.clave,
                    "nombre_actual": resultado.autoridad.descripcion_corta,
                    "url_actual": (
                        url_for("autoridades.detail", autoridad_id=resultado.autoridad.id)
                        if current_user.can_view("AUTORIDADES")
                        else ""
                    ),
                    "origenes": resultado.arc_juzgados_origen_claves if resultado.arc_juzgados_origen_claves != None else "",
                },
                "anio": resultado.anio,
                "tipo": resultado.arc_documento_tipo.nombre,
                "fojas": resultado.fojas,
                "actor": resultado.actor,
                "juicio": resultado.juicio,
                "demandado": resultado.demandado,
                "ubicacion": resultado.ubicacion,
                "partes": {
                    "actor": resultado.actor,
                    "demandado": resultado.demandado,
                },
            }
        )
    # Entregar JSON
    return output_datatable_json(draw, total, data)


@arc_documentos.route("/arc_documentos")
def list_active():
    """Listado de Documentos activos"""

    # Consultar los roles del usuario
    current_user_roles = current_user.get_roles()

    if current_user.can_admin(MODULO) or ROL_JEFE_REMESA_ADMINISTRADOR in current_user_roles:
        return render_template(
            "arc_documentos/list_admin.jinja2",
            filtros=json.dumps({"estatus": "A"}),
            titulo="Expedientes",
            estatus="A",
            ubicaciones=ArcDocumento.UBICACIONES,
        )

    if (
        ROL_JEFE_REMESA in current_user_roles
        or ROL_ARCHIVISTA in current_user_roles
        or ROL_LEVANTAMENTISTA in current_user_roles
    ):
        return render_template(
            "arc_documentos/list_admin.jinja2",
            filtros=json.dumps({"estatus": "A", "sede": current_user.autoridad.sede}),
            titulo="Expedientes",
            estatus="A",
            ubicaciones=ArcDocumento.UBICACIONES,
        )

    return render_template(
        "arc_documentos/list.jinja2",
        filtros=json.dumps({"estatus": "A", "juzgado_id": current_user.autoridad.id}),
        titulo=f"Expedientes del {current_user.autoridad.descripcion_corta}",
        estatus="A",
        ubicaciones=ArcDocumento.UBICACIONES,
    )


@arc_documentos.route("/arc_documentos/<int:documento_id>")
def detail(documento_id):
    """Detalle de un Documento"""
    documento = ArcDocumento.query.get_or_404(documento_id)

    # mostrar secciones según el ROL
    mostrar_secciones = {}
    current_user_roles = current_user.get_roles()

    if current_user.can_admin(MODULO):
        mostrar_secciones["boton_eliminar"] = True

    if current_user.can_edit(MODULO):
        mostrar_secciones["boton_editar"] = True

    if (
        current_user.can_admin(MODULO)
        or ROL_JEFE_REMESA in current_user_roles
        or ROL_JEFE_REMESA_ADMINISTRADOR in current_user_roles
        or ROL_SOLICITANTE in current_user_roles
    ):
        mostrar_secciones["boton_editar"] = True
        if current_user.can_insert(MODULO) and documento.ubicacion == "ARCHIVO":
            documento_en_proceso = (
                ArcSolicitud.query.filter_by(arc_documento=documento)
                .filter_by(esta_archivado=False)
                .filter_by(estatus="A")
                .first()
            )
            if not documento_en_proceso:
                mostrar_secciones["boton_solicitar"] = True
        return render_template(
            "arc_documentos/detail.jinja2",
            documento=documento,
            acciones=ArcDocumentoBitacora.ACCIONES,
            mostrar_secciones=mostrar_secciones,
        )

    if ROL_LEVANTAMENTISTA in current_user_roles:
        mostrar_secciones["boton_editar"] = True
        return render_template(
            "arc_documentos/detail_simple.jinja2",
            documento=documento,
            mostrar_secciones=mostrar_secciones,
        )

    return render_template(
        "arc_documentos/detail_simple.jinja2",
        documento=documento,
        acciones=ArcDocumentoBitacora.ACCIONES,
        mostrar_secciones=mostrar_secciones,
    )
