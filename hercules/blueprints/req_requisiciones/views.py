"""
Req Requisiciones, vistas
"""

import json
from datetime import datetime
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

from hercules.blueprints.req_catalogos.models import ReqCatalogo
from hercules.blueprints.req_requisiciones_registros.models import ReqRequisicionRegistro
from hercules.blueprints.req_requisiciones.forms import ReqRequisicionNewForm


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
    current_user_roles = current_user.get_roles()
    # Si es asistente, mostrar TODAS las Requisiciones de su oficina
    req_requisicion = ReqRequisicion.query.get_or_404(req_requisicion_id)
    articulos = ReqRequisicionRegistro.query.filter_by(req_requisicion_id=req_requisicion_id).join(ReqCatalogo).all()
    usuario = Usuario.query.get_or_404(req_requisicion.usuario_id) if req_requisicion.usuario_id > 0 else ""
    usuario_solicito = Usuario.query.get_or_404(req_requisicion.solicito_id) if req_requisicion.solicito_id > 0 else ""
    usuario_autorizo = Usuario.query.get_or_404(req_requisicion.autorizo_id) if req_requisicion.autorizo_id > 0 else ""
    usuario_reviso = Usuario.query.get_or_404(req_requisicion.reviso_id) if req_requisicion.reviso_id > 0 else ""
    autoridad = Autoridad.query.get_or_404(req_requisicion.usuario.autoridad_id)
    return render_template(
        "req_requisiciones/detail.jinja2",
        req_requisicion=req_requisicion,
        req_requisicion_registro=articulos,
        usuario=usuario,
        autoridad=autoridad,
        usuario_solicito=usuario_solicito,
        usuario_autorizo=usuario_autorizo,
        usuario_reviso=usuario_reviso,
        current_user_roles=current_user_roles,
    )


@req_requisiciones.route("/req_requisiciones/buscarRegistros/", methods=["GET"])
def buscarRegistros():
    args = request.args
    registro = ReqCatalogo.query.get_or_404(args.get("req_catalogo_id"))
    return ReqCatalogo.object_as_dict(registro)


@req_requisiciones.route("/req_requisiciones/nuevo", methods=["GET", "POST"])
@permission_required(MODULO, Permiso.CREAR)
def new():
    """Requisiciones nueva"""
    form = ReqRequisicionNewForm()
    form.claveTmp.choices = [("", "")] + [
        (c.id, c.clave + " - " + c.descripcion) for c in ReqCatalogo.query.order_by("descripcion")
    ]
    form.cveTmp.choices = (
        [("", "")]
        + [("INS", "INSUFICIENCIA")]
        + [("REP", "REPOSICION DE BIENES")]
        + [("OBS", "OBSOLESENCIA")]
        + [("AMP", "AMPLIACION COBERTURA DEL SERVICIO")]
        + [("NUE", "NUEVO PROYECTO")]
    )
    if form.validate_on_submit():
        # Guardar requisicion
        req_requisicion = ReqRequisicion(
            usuario=current_user,
            estado="BORRADOR",
            observaciones=safe_string(form.observaciones.data, max_len=256, to_uppercase=True, save_enie=True),
            justificacion=safe_string(form.justificacion.data, max_len=1024, to_uppercase=True, save_enie=True),
            fecha=datetime.now(),
            gasto=safe_string(form.gasto.data, to_uppercase=True, save_enie=True),
            glosa=form.glosa.data,
            programa=safe_string(form.programa.data, to_uppercase=True, save_enie=True),
            fuente_financiamiento=safe_string(form.fuente_financiamiento.data, to_uppercase=True, save_enie=True),
            fecha_requerida=form.fechaRequerida.data,
            solicito_id=0,
            autorizo_id=0,
            reviso_id=0,
        )
        req_requisicion.save()
        # Guardar los registros de la requisición
        for registros in form.articulos:
            if registros.clave.data != None:
                req_requisicion_registro = ReqRequisicionRegistro(
                    req_requisicion_id=req_requisicion.id,
                    req_catalogo_id=registros.clave.data,
                    # clave=registros.clave.data,
                    cantidad=registros.cantidad.data,
                    detalle=registros.detalle.data,
                )
                req_requisicion_registro.save()

        # Guardar en la bitacora
        bitacora = Bitacora(
            modulo=Modulo.query.filter_by(nombre=MODULO).first(),
            usuario=current_user,
            descripcion=safe_message(f"Requisicion creada {req_requisicion.observaciones}"),
            url=url_for("req_requisiciones.detail", req_requisicion_id=req_requisicion.id),
        )
        bitacora.save()
        flash(bitacora.descripcion, "success")
        return redirect(bitacora.url)
    return render_template(
        "req_requisiciones/new.jinja2", titulo="Nueva Requisición", form=form, area=current_user.autoridad.descripcion
    )


@req_requisiciones.route("/req_requisiciones/<req_requisicion_id>/eliminar")
@permission_required(MODULO, Permiso.MODIFICAR)
def delete(req_requisicion_id):
    print("Inicia el proceso de borrado")
    """Eliminar Requisición"""
    req_requisicion = ReqRequisicion.query.get_or_404(req_requisicion_id)
    if req_requisicion.estatus == "A":
        puede_eliminarlo = False
        if current_user.can_admin(MODULO):
            puede_eliminarlo = True
        if req_requisicion.usuario == current_user and req_requisicion.estado == "BORRADOR":
            puede_eliminarlo = True
        if not puede_eliminarlo:
            flash("No tiene permisos para eliminar o tiene un estado particular", "warning")
            return redirect(url_for("req_requisiciones.detail", req_requisicion_id=req_requisicion_id))
        req_requisicion.delete()
        bitacora = Bitacora(
            modulo=Modulo.query.filter_by(nombre=MODULO).first(),
            usuario=current_user,
            descripcion=safe_message(f"Eliminada Requisición {req_requisicion.justificacion}"),
            url=url_for("req_requisiciones.detail", req_requisicion_id=req_requisicion.id),
        )
        bitacora.save()
        flash(bitacora.descripcion, "success")
    return redirect(url_for("req_requisiciones.detail", req_requisicion_id=req_requisicion.id))


@req_requisiciones.route("/req_requisiciones/recuperar/<req_requisicion_id>")
@permission_required(MODULO, Permiso.MODIFICAR)
def recover(req_requisicion_id):
    """Recuperar Requisición"""
    req_requisicion = ReqRequisicion.query.get_or_404(req_requisicion_id)
    if req_requisicion.estatus == "B":
        req_requisicion.recover()
        bitacora = Bitacora(
            modulo=Modulo.query.filter_by(nombre=MODULO).first(),
            usuario=current_user,
            descripcion=safe_message(f"Recuperado Requisición {req_requisicion.id}"),
            url=url_for("req_requisiciones.detail", req_requisicion_id=req_requisicion.id),
        )
        bitacora.save()
        flash(bitacora.descripcion, "success")
    return redirect(url_for("req_requisiciones.detail", req_requisicion_id=req_requisicion.id))


@req_requisiciones.route("/req_requisiciones/<req_requisicion_id>/imprimir")
def detail_print(req_requisicion_id):
    """Impresion de la Requsición"""

    # Consultar la requisición
    req_requisicion = ReqRequisicion.query.get_or_404(req_requisicion_id)
    articulos = (
        ReqRequisicionRegistro.query.filter_by(req_requisicion_id=req_requisicion_id)
        .join(ReqCatalogo)
        .add_columns(ReqCatalogo)
        .all()
    )
    usuario = Usuario.query.get_or_404(req_requisicion.usuario_id)
    usuario_solicito = Usuario.query.get_or_404(req_requisicion.solicito_id) if req_requisicion.solicito_id > 0 else ""
    usuario_autorizo = Usuario.query.get_or_404(req_requisicion.autorizo_id) if req_requisicion.autorizo_id > 0 else ""
    usuario_reviso = Usuario.query.get_or_404(req_requisicion.reviso_id) if req_requisicion.reviso_id > 0 else ""

    # Validar que pueda verla
    puede_imprimirlo = False

    # Si es administrador, puede imprimirla
    if current_user.can_admin(MODULO):
        puede_imprimirlo = True

    # Si tiene uno de los roles que pueden imprimir y esta activo, puede imprimirla
    # if set(current_user.get_roles()).intersection(ROLES_PUEDEN_IMPRIMIR) and req_requisicion.estatus == "A":
    #     puede_imprimirlo = True

    # Si es el usuario que lo creo y esta activo, puede imprimirla
    if req_requisicion.usuario_id == current_user.id and req_requisicion.estatus == "A":
        puede_imprimirlo = True

    # Si puede imprimirla
    if puede_imprimirlo:
        # Mostrar la plantilla para imprimir
        return render_template(
            "req_requisiciones/print.jinja2",
            req_requisicion=req_requisicion,
            req_requisicion_registro=articulos,
            usuario=usuario,
            usuario_solicito=usuario_solicito,
            usuario_autorizo=usuario_autorizo,
            usuario_reviso=usuario_reviso,
        )

    # No puede imprimirla
    flash("No tiene permiso para imprimir la requisición", "warning")
    return redirect(url_for("req_requisiciones.list_active"))


@req_requisiciones.route("/req_requisiciones/<req_requisicion_id>/generarpdf")
def create_pdf(req_requisicion_id):
    """Impresion de la Requsición"""

    # Consultar la requisición
    req_requisicion = ReqRequisicion.query.get_or_404(req_requisicion_id)

    # Validar que pueda verla
    puede_imprimirlo = False

    # Si es administrador, puede imprimirla
    if current_user.can_admin(MODULO):
        puede_imprimirlo = True

    # Si es el usuario que lo creo y esta activo, puede imprimirla
    if req_requisicion.usuario_id == current_user.id and req_requisicion.estatus == "A":
        puede_imprimirlo = True

    # Si puede imprimirla
    if puede_imprimirlo:

        current_user.launch_task(
            comando="req_requisiciones.tasks.lanzar_convertir_requisicion_a_pdf",
            mensaje="Convirtiendo a archivo PDF...",
            req_requisicion_id=str(req_requisicion_id),
        )
        # Agregar registro a la bitácora
        bitacora = Bitacora(
            modulo=Modulo.query.filter_by(nombre=MODULO).first(),
            usuario=current_user,
            descripcion=safe_message(f"Generar PDf de requisicion {req_requisicion.id}"),
            url=url_for("req_requisiciones.detail", req_requisicion_id=req_requisicion.id),
        )
        bitacora.save()
        flash(bitacora.descripcion, "success")
        return redirect(bitacora.url)

    # No puede imprimirla
    flash("No tiene permiso para imprimir la requisición", "warning")
    return redirect(url_for("req_requisiciones.list_active"))
