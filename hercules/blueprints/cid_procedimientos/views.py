"""
CID Procedimientos, vistas
"""

import json

from delta import html
from flask import Blueprint, flash, redirect, render_template, request, url_for
from flask_login import current_user, login_required

from hercules.blueprints.bitacoras.models import Bitacora
from hercules.blueprints.cid_procedimientos.models import CIDProcedimiento
from hercules.blueprints.modulos.models import Modulo
from hercules.blueprints.permisos.models import Permiso
from hercules.blueprints.usuarios.decorators import permission_required
from lib.datatables import get_datatable_parameters, output_datatable_json
from lib.safe_string import safe_clave, safe_message, safe_string

MODULO = "CID PROCEDIMIENTOS"

cid_procedimientos = Blueprint("cid_procedimientos", __name__, template_folder="templates")

# Roles que deben estar en la base de datos
ROL_ADMINISTRADOR = "ADMINISTRADOR"
ROL_COORDINADOR = "SICGD COORDINADOR"
ROL_DIRECTOR_JEFE = "SICGD DIRECTOR O JEFE"
ROL_DUENO_PROCESO = "SICGD DUENO DE PROCESO"
ROL_INVOLUCRADO = "SICGD INVOLUCRADO"
ROLES_CON_PROCEDIMIENTOS_PROPIOS = (ROL_COORDINADOR, ROL_DIRECTOR_JEFE, ROL_DUENO_PROCESO)
ROLES_NUEVA_REVISION = (ROL_COORDINADOR, ROL_DUENO_PROCESO)


@cid_procedimientos.before_request
@login_required
@permission_required(MODULO, Permiso.VER)
def before_request():
    """Permiso por defecto"""


@cid_procedimientos.route("/cid_procedimientos/datatable_json", methods=["GET", "POST"])
def datatable_json():
    """DataTable JSON para listado de CID Procedimientos"""
    # Tomar parámetros de Datatables
    draw, start, rows_per_page = get_datatable_parameters()
    # Consultar
    consulta = CIDProcedimiento.query
    # Primero filtrar por columnas propias
    if "estatus" in request.form:
        consulta = consulta.filter_by(estatus=request.form["estatus"])
    else:
        consulta = consulta.filter_by(estatus="A")
    if "codigo" in request.form:
        try:
            codigo = safe_clave(request.form["codigo"])
            if codigo != "":
                consulta = consulta.filter(CIDProcedimiento.codigo.contains(codigo))
        except ValueError:
            pass
    if "seguimiento" in request.form:
        consulta = consulta.filter(CIDProcedimiento.seguimiento == request.form["seguimiento"])
    if "titulo_procedimiento" in request.form:
        titulo_procedimiento = safe_string(request.form["titulo_procedimiento"], save_enie=True)
        if titulo_procedimiento != "":
            consulta = consulta.filter(CIDProcedimiento.titulo_procedimiento.contains(titulo_procedimiento))
    # if "usuario_id" in request.form:
    #     consulta = consulta.filter(CIDProcedimiento.usuario_id == request.form["usuario_id"])
    if "seguimiento_posterior" in request.form:
        consulta = consulta.filter(CIDProcedimiento.seguimiento_posterior != request.form["seguimiento_posterior"])
    # if "cid_areas[]" in request.form:
    #     areas_a_filtrar = request.form.getlist("cid_areas[]")
    #     listado_areas_ids = [int(area_id) for area_id in areas_a_filtrar]
    #     consulta = consulta.filter(CIDProcedimiento.cid_area_id.in_(listado_areas_ids))
    # Ordenar y paginar
    registros = consulta.order_by(CIDProcedimiento.titulo_procedimiento).offset(start).limit(rows_per_page).all()
    total = consulta.count()
    # Elaborar datos para DataTable
    data = []
    for resultado in registros:
        data.append(
            {
                "detalle": {
                    "codigo": resultado.codigo,
                    "url": url_for("cid_procedimientos.detail", cid_procedimiento_id=resultado.id),
                },
                "titulo_procedimiento": resultado.titulo_procedimiento,
                "revision": resultado.revision,
                "elaboro_nombre": resultado.elaboro_email,
                "fecha": resultado.fecha.strftime("%Y-%m-%d"),
                "seguimiento": resultado.seguimiento,
                "seguimiento_posterior": resultado.seguimiento_posterior,
                # "usuario": {
                #     "nombre": resultado.usuario.nombre,
                #     "url": (
                #         url_for("usuarios.detail", usuario_id=resultado.usuario_id) if current_user.can_view("USUARIOS") else ""
                #     ),
                # },
                # "autoridad": resultado.autoridad.clave,
                # "cid_area": {
                #     "clave": resultado.cid_area.clave,
                #     "url": (
                #         url_for("cid_areas.detail", cid_area_id=resultado.cid_area_id)
                #         if current_user.can_view("CID AREAS")
                #         else ""
                #     ),
                # },
            }
        )
    # Entregar JSON
    return output_datatable_json(draw, total, data)


@cid_procedimientos.route("/cid_procedimientos/datatable_json_admin", methods=["GET", "POST"])
def datatable_json_admin():
    """DataTable JSON para listado de Cid Procedimientos"""
    # Tomar parámetros de Datatables
    draw, start, rows_per_page = get_datatable_parameters()
    # Consultar
    consulta = CIDProcedimiento.query
    # Primero filtrar por columnas propias
    if "estatus" in request.form:
        consulta = consulta.filter_by(estatus=request.form["estatus"])
    else:
        consulta = consulta.filter_by(estatus="A")
    if "cid_procedmiento_id" in request.form:
        try:
            cid_procedimiento_id = int(request.form["cid_procedmiento_id"])
            consulta = consulta.filter(CIDProcedimiento.id == cid_procedimiento_id)
        except ValueError:
            pass
    if "codigo" in request.form:
        try:
            codigo = safe_clave(request.form["codigo"])
            if codigo != "":
                consulta = consulta.filter(CIDProcedimiento.codigo.contains(codigo))
        except ValueError:
            pass
    if "seguimiento" in request.form:
        consulta = consulta.filter(CIDProcedimiento.seguimiento == request.form["seguimiento"])
    if "titulo_procedimiento" in request.form:
        titulo_procedimiento = safe_string(request.form["titulo_procedimiento"], save_enie=True)
        if titulo_procedimiento != "":
            consulta = consulta.filter(CIDProcedimiento.titulo_procedimiento.contains(titulo_procedimiento))
    # if "usuario_id" in request.form:
    #     consulta = consulta.filter(CIDProcedimiento.usuario_id == request.form["usuario_id"])
    if "seguimiento_posterior" in request.form:
        consulta = consulta.filter(CIDProcedimiento.seguimiento_posterior != request.form["seguimiento_posterior"])
    # if "cid_areas[]" in request.form:
    #     areas_a_filtrar = request.form.getlist("cid_areas[]")
    #     listado_areas_ids = [int(area_id) for area_id in areas_a_filtrar]
    #     consulta = consulta.filter(CIDProcedimiento.cid_area_id.in_(listado_areas_ids))
    # Ordenar y paginar
    registros = consulta.order_by(CIDProcedimiento.id.desc()).offset(start).limit(rows_per_page).all()
    total = consulta.count()
    # Elaborar datos para DataTable
    data = []
    for resultado in registros:
        data.append(
            {
                "detalle": {
                    "id": resultado.id,
                    "url": url_for("cid_procedimientos.detail", cid_procedimiento_id=resultado.id),
                },
                "titulo_procedimiento": resultado.titulo_procedimiento,
                "codigo": resultado.codigo,
                "revision": resultado.revision,
                "elaboro_nombre": resultado.elaboro_email,
                "fecha": resultado.fecha.strftime("%Y-%m-%d"),
                "seguimiento": resultado.seguimiento,
                "seguimiento_posterior": resultado.seguimiento_posterior,
                # "usuario": {
                #     "nombre": resultado.usuario.nombre,
                #     "url": (
                #         url_for("usuarios.detail", usuario_id=resultado.usuario_id) if current_user.can_view("USUARIOS") else ""
                #     ),
                # },
                # "autoridad": resultado.autoridad.clave,
                # "cid_area": {
                #     "clave": resultado.cid_area.clave,
                #     "url": (
                #         url_for("cid_areas.detail", cid_area_id=resultado.cid_area_id)
                #         if current_user.can_view("CID AREAS")
                #         else ""
                #     ),
                # },
            }
        )
    # Entregar JSON
    return output_datatable_json(draw, total, data)


@cid_procedimientos.route("/cid_procedimientos")
def list_active():
    """Listado de CID Procedimientos activos"""
    # Consultar los roles del usuario
    current_user_roles = set(current_user.get_roles())
    # Si es administrador, usar list_admin.jinja2
    if current_user.can_admin(MODULO) and ROL_ADMINISTRADOR in current_user_roles:
        return render_template(
            "cid_procedimientos/list_admin.jinja2",
            titulo="Procedimientos autorizados de mis áreas",
            filtros=json.dumps({"estatus": "A", "seguimiento": "AUTORIZADO"}),
            estatus="A",
            show_button_list_owned=current_user_roles.intersection(ROLES_CON_PROCEDIMIENTOS_PROPIOS),
            show_button_list_all=ROL_COORDINADOR in current_user_roles,
            show_button_list_all_autorized=True,
            show_button_my_autorized=False,
            show_lista_maestra=ROL_COORDINADOR in current_user_roles,
        )
    # De lo contrario, usar list.jinja2
    return render_template(
        "cid_procedimientos/list.jinja2",
        titulo="Procedimientos autorizados de mis áreas",
        filtros=json.dumps({"estatus": "A", "seguimiento": "AUTORIZADO", "seguimiento_posterior": "ARCHIVADO"}),
        estatus="A",
        show_button_list_owned=current_user_roles.intersection(ROLES_CON_PROCEDIMIENTOS_PROPIOS),
        show_button_list_all=current_user.can_admin(MODULO) or ROL_COORDINADOR in current_user_roles,
        show_button_list_all_autorized=True,
        show_button_my_autorized=False,
        show_lista_maestra=current_user.can_admin(MODULO) or ROL_COORDINADOR in current_user_roles,
    )


@cid_procedimientos.route("/cid_procedimientos/autorizados")
def list_authorized():
    """Listado de todos los procedimientos autorizados"""
    # Consultar los roles del usuario
    current_user_roles = set(current_user.get_roles())
    # Si es administrador, usar list_admin.jinja2
    if current_user.can_admin(MODULO) and ROL_ADMINISTRADOR in current_user_roles:
        return render_template(
            "cid_procedimientos/list_admin.jinja2",
            titulo="Todos los procedimientos autorizados",
            filtros=json.dumps({"estatus": "A", "seguimiento": "AUTORIZADO", "seguimiento_posterior": "ARCHIVADO"}),
            estatus="A",
            show_button_list_owned=current_user_roles.intersection(ROLES_CON_PROCEDIMIENTOS_PROPIOS),
            show_button_list_all=ROL_COORDINADOR in current_user_roles,
            show_button_list_all_autorized=False,
            show_button_my_autorized=True,
            show_lista_maestra=ROL_COORDINADOR in current_user_roles,
        )
    # De lo contrario, usar list.jinja2
    return render_template(
        "cid_procedimientos/list.jinja2",
        titulo="Todos los procedimientos autorizados",
        filtros=json.dumps({"estatus": "A", "seguimiento": "AUTORIZADO", "seguimiento_posterior": "ARCHIVADO"}),
        estatus="A",
        show_button_list_owned=current_user_roles.intersection(ROLES_CON_PROCEDIMIENTOS_PROPIOS),
        show_button_list_all=current_user.can_admin(MODULO) or ROL_COORDINADOR in current_user_roles,
        show_button_list_all_autorized=False,
        show_button_my_autorized=True,
        show_lista_maestra=current_user.can_admin(MODULO) or ROL_COORDINADOR in current_user_roles,
    )


@cid_procedimientos.route("/cid_procedimientos/propios")
def list_owned():
    """Listado de procedimientos propios"""

    # Consultar los roles del usuario
    current_user_roles = set(current_user.get_roles())

    # Si es administrador, usar list_admin.jinja2
    if current_user.can_admin(MODULO) and ROL_ADMINISTRADOR in current_user_roles:
        return render_template(
            "cid_procedimientos/list_admin.jinja2",
            # cid_procedimiento=procedimientos_archivados_list,
            titulo="Procedimientos propios",
            filtros=json.dumps({"estatus": "A", "usuario_id": current_user.id, "seguimiento_posterior": "ARCHIVADO"}),
            estatus="A",
            show_button_list_owned=False,
            show_button_list_all=ROL_COORDINADOR in current_user_roles,
            show_button_list_all_autorized=True,
            show_button_my_autorized=True,
            show_lista_maestra=ROL_COORDINADOR in current_user_roles,
        )
    # De lo contrario, usar list.jinja2
    return render_template(
        "cid_procedimientos/list.jinja2",
        # cid_procedimiento=procedimientos_archivados_list,
        titulo="Procedimientos propios",
        filtros=json.dumps({"estatus": "A", "usuario_id": current_user.id, "seguimiento_posterior": "ARCHIVADO"}),
        estatus="A",
        show_button_list_owned=False,
        show_button_list_all=current_user.can_admin(MODULO) or ROL_COORDINADOR in current_user_roles,
        show_button_list_all_autorized=True,
        show_button_my_autorized=True,
        show_lista_maestra=current_user.can_admin(MODULO) or ROL_COORDINADOR in current_user_roles,
    )


@cid_procedimientos.route("/cid_procedimientos/activos")
@permission_required(MODULO, Permiso.ADMINISTRAR)
def list_all_active():
    """Listado de procedimientos activos, solo para administrador"""
    # Consultar los roles del usuario
    current_user_roles = set(current_user.get_roles())
    # Si es administrador, usar list_admin.jinja2
    if current_user.can_admin(MODULO) and ROL_ADMINISTRADOR in current_user_roles:
        return render_template(
            "cid_procedimientos/list_admin.jinja2",
            titulo="Todos los procedimientos activos",
            filtros=json.dumps({"estatus": "A"}),
            estatus="A",
            show_button_list_owned=True,
            show_button_list_all=False,
            show_button_list_all_autorized=True,
            show_button_my_autorized=True,
            show_lista_maestra=True,
        )
    return render_template(
        "cid_procedimientos/list.jinja2",
        titulo="Todos los procedimientos activos",
        filtros=json.dumps({"estatus": "A"}),
        estatus="A",
        show_button_list_owned=True,
        show_button_list_all=False,
        show_button_list_all_autorized=True,
        show_button_my_autorized=True,
        show_lista_maestra=True,
    )


@cid_procedimientos.route("/cid_procedimientos/eliminados")
@permission_required(MODULO, Permiso.ADMINISTRAR)
def list_all_inactive():
    """Listado de procedimientos eliminados, solo para administrador"""
    # Consultar los roles del usuario
    current_user_roles = set(current_user.get_roles())
    return render_template(
        "cid_procedimientos/list_admin.jinja2",
        titulo="Todos los procedimientos eliminados",
        filtros=json.dumps({"estatus": "B"}),
        estatus="B",
        show_button_list_owned=True,
        show_button_list_all=current_user.can_admin(MODULO) or ROL_COORDINADOR in current_user_roles,
        show_button_list_all_autorized=True,
        show_button_my_autorized=True,
        show_lista_maestra=current_user.can_admin(MODULO) or ROL_COORDINADOR in current_user_roles,
    )


@cid_procedimientos.route("/cid_procedimientos/<int:cid_procedimiento_id>")
def detail(cid_procedimiento_id):
    """Detalle de un Cid Procedimiento"""
    # Consultar los roles del usuario
    current_user_roles = set(current_user.get_roles())
    cid_procedimiento = CIDProcedimiento.query.get_or_404(cid_procedimiento_id)

    return render_template(
        "cid_procedimientos/detail.jinja2",
        cid_procedimiento=cid_procedimiento,
        firma_al_vuelo=cid_procedimiento.elaborar_firma(),
        objetivo=str(html.render(cid_procedimiento.objetivo["ops"])),
        alcance=str(html.render(cid_procedimiento.alcance["ops"])),
        documentos=str(html.render(cid_procedimiento.documentos["ops"])),
        definiciones=str(html.render(cid_procedimiento.definiciones["ops"])),
        responsabilidades=str(html.render(cid_procedimiento.responsabilidades["ops"])),
        desarrollo=str(html.render(cid_procedimiento.desarrollo["ops"])),
        registros=cid_procedimiento.registros,
        control_cambios=cid_procedimiento.control_cambios,
        # cid_formatos=cid_formatos,
        show_button_edit_admin=current_user.can_admin(MODULO) or ROL_COORDINADOR in current_user.get_roles(),
        # show_cambiar_area=show_cambiar_area,
        show_buttom_new_revision=current_user_roles.intersection(ROLES_NUEVA_REVISION),
    )
