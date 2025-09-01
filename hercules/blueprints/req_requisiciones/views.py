"""
Req Requisiciones, vistas
"""

from datetime import datetime
import json

from flask import Blueprint, current_app, flash, make_response, redirect, render_template, request, url_for
from flask_login import current_user, login_required
from werkzeug.exceptions import NotFound

from lib.datatables import get_datatable_parameters, output_datatable_json
from lib.safe_string import safe_string, safe_message, safe_uuid
from lib.exceptions import MyBucketNotFoundError, MyFileNotFoundError, MyNotValidParamError
from lib.google_cloud_storage import get_blob_name_from_url, get_file_from_gcs

from hercules.blueprints.bitacoras.models import Bitacora
from hercules.blueprints.modulos.models import Modulo
from hercules.blueprints.permisos.models import Permiso
from hercules.blueprints.usuarios.decorators import permission_required
from hercules.blueprints.req_requisiciones.models import ReqRequisicion
from hercules.blueprints.req_requisiciones.forms import (
    ReqRequisicionNewForm,
    ReqRequisicionCancel3AuthorizeForm,
    ReqRequisicionCancel4ReviewForm,
)
from hercules.blueprints.autoridades.models import Autoridad
from hercules.blueprints.req_catalogos.models import ReqCatalogo
from hercules.blueprints.req_requisiciones_registros.models import ReqRequisicionRegistro
from hercules.blueprints.usuarios.models import Usuario
from hercules.extensions import database

MODULO = "REQ REQUISICIONES"

req_requisiciones = Blueprint("req_requisiciones", __name__, template_folder="templates")

# Roles que deben estar en la base de datos
ROL_ASISTENTES = "REQUISICIONES ASISTENTES"
ROL_SOLICITANTES = "REQUISICIONES SOLICITANTES"
ROL_AUTORIZANTES = "REQUISICIONES AUTORIZANTES"
ROL_REVISANTES = "REQUISICIONES REVISANTES"

ROLES_PUEDEN_VER = (ROL_SOLICITANTES, ROL_AUTORIZANTES, ROL_REVISANTES, ROL_ASISTENTES)
ROLES_PUEDEN_IMPRIMIR = (ROL_SOLICITANTES, ROL_AUTORIZANTES, ROL_REVISANTES, ROL_ASISTENTES)


@req_requisiciones.before_request
@login_required
@permission_required(MODULO, Permiso.VER)
def before_request():
    """Permiso por defecto"""


@req_requisiciones.route("/req_requisiciones/datatable_json", methods=["GET", "POST"])
def datatable_json():
    """DataTable JSON para listado de Requisiciones"""
    # Tomar parámetros de Datatables
    draw, start, rows_per_page = get_datatable_parameters()
    # Consultar
    consulta = ReqRequisicion.query

    if "estado" in request.form:
        consulta = consulta.filter_by(estado=request.form["estado"])
    if "autoridad" in request.form:
        consulta = consulta.filter_by(autoridad_id=request.form["autoridad"])
    if "solicito_id" in request.form:
        consulta = consulta.filter_by(solicito_id=request.form["solicito_id"])
    if "estatus" in request.form:
        consulta = consulta.filter_by(estatus=request.form["estatus"])
    else:
        consulta = consulta.filter_by(estatus="A")
    if "glosa" in request.form:
        consulta = consulta.filter(ReqRequisicion.glosa.contains(safe_string(request.form["glosa"], to_uppercase=False)))
    if "observaciones" in request.form:
        consulta = consulta.filter(
            ReqRequisicion.observaciones.contains(safe_string(request.form["observaciones"], to_uppercase=True))
        )
    registros = consulta.order_by(ReqRequisicion.id).offset(start).limit(rows_per_page).all()

    total = consulta.count()
    # Elaborar datos para DataTable
    data = []
    for resultado in registros:
        oficina = ""

        autoridad = Autoridad.query.filter_by(id=resultado.autoridad_id)
        for row in autoridad:
            clave = row.clave
            nombre = row.descripcion

        data.append(
            {
                "id": resultado.id,
                "folio": resultado.gasto,
                "estado": resultado.estado,
                "oficina": oficina,
                "autoridad": {
                    "nombre": nombre,
                    "clave": clave,
                },
                "creado": resultado.usuario.nombre,
                "usuario": resultado.usuario.nombre,
                "nombre": resultado.usuario.nombre,
                "fecha": resultado.fecha,
                "glosa": resultado.glosa,
                "justificacion": resultado.justificacion,
                "detalle": {
                    "gasto": resultado.gasto,
                    "url": url_for("req_requisiciones.detail", req_requisicion_id=resultado.id),
                    "icono": "",
                },
                "observaciones": resultado.observaciones[0:50],
            }
        )
    # Entregar JSON
    return output_datatable_json(draw, total, data)


@req_requisiciones.route("/req_requisiciones")
def list_active():
    """Listado de Requisiciones activos"""

    # Si es administrador puede ver TODAS las requisiciones
    if current_user.can_admin(MODULO):
        return render_template(
            "req_requisiciones/list.jinja2",
            filtros=json.dumps({"estatus": "A"}),
            titulo="Administrar las Requisiciones",
            estatus="A",
        )
    # Consultar los roles del usuario
    current_user_roles = current_user.get_roles()
    # Si es asistente, mostrar TODAS las Requisiciones de su oficina
    if ROL_ASISTENTES in current_user_roles:
        return render_template(
            "req_requisiciones/list.jinja2",
            filtros=json.dumps({"estatus": "A", "autoridad": current_user.autoridad_id}),
            titulo="Requisiciones de mi oficina",
            estatus="A",
        )
    # Si es solicitante, mostrar Requisiciones por Solicitar
    if ROL_SOLICITANTES in current_user_roles:
        return render_template(
            "req_requisiciones/list.jinja2",
            filtros=json.dumps({"estatus": "A", "solicito_id": current_user.id}),
            titulo="Requisiciones Solicitadas",
            estatus="A",
        )
    # Si es autorizante, mostrar Requisiciones por Autorizar
    if ROL_AUTORIZANTES in current_user_roles:
        return render_template(
            "req_requisiciones/list.jinja2",
            filtros=json.dumps({"estatus": "A", "estado": "SOLICITADO"}),
            titulo="Requisiciones Solicitadas (por autorizar)",
            estatus="A",
        )
    if ROL_REVISANTES in current_user_roles:
        return render_template(
            "req_requisiciones/list.jinja2",
            filtros=json.dumps({"estatus": "A", "estado": "AUTORIZADO"}),
            titulo="Requisiciones Autorizadas (por revisar)",
            estatus="A",
        )
    # Mostrar Mis Requisiciones
    return render_template(
        "req_requisiciones/list.jinja2",
        filtros=json.dumps({"estatus": "A", "usuario_id": current_user.id}),
        titulo="Mis Requisiciones",
        estatus="A",
    )


@req_requisiciones.route("/req_requisiciones/mi_autoridad")
def list_active_mi_autoridad():
    """Listado de Requisiciones activos"""

    # Si es administrador puede ver TODAS las requisiciones
    if current_user.can_admin(MODULO):
        return render_template(
            "req_requisiciones/list.jinja2",
            filtros=json.dumps({"estatus": "A"}),
            titulo="Administrar las Requisiciones",
            estatus="A",
        )
    # Consultar los roles del usuario
    current_user_roles = current_user.get_roles()
    # Si es asistente, mostrar TODAS las Requisiciones de su oficina
    if ROL_ASISTENTES in current_user_roles:
        return render_template(
            "req_requisiciones/list.jinja2",
            filtros=json.dumps({"estatus": "A", "autoridad": current_user.autoridad_id}),
            titulo="Requisiciones de mi oficina",
            estatus="A",
        )
    # Si es solicitante, mostrar Requisiciones por Solicitar
    if ROL_SOLICITANTES in current_user_roles:
        return render_template(
            "req_requisiciones/list.jinja2",
            filtros=json.dumps({"estatus": "A", "autoridad": current_user.autoridad_id}),
            titulo="Requisiciones Solicitadas",
            estatus="A",
        )
    # Si es autorizante, mostrar Requisiciones por Autorizar
    if ROL_AUTORIZANTES in current_user_roles:
        return render_template(
            "req_requisiciones/list.jinja2",
            filtros=json.dumps({"estatus": "A", "estado": "SOLICITADO"}),
            titulo="Requisiciones Solicitadas (por autorizar)",
            estatus="A",
        )
    if ROL_REVISANTES in current_user_roles:
        return render_template(
            "req_requisiciones/list.jinja2",
            filtros=json.dumps({"estatus": "A", "estado": "AUTORIZADO"}),
            titulo="Requisiciones Autorizadas (por revisar)",
            estatus="A",
        )
    # Mostrar Mis Requisiciones
    return render_template(
        "req_requisiciones/list.jinja2",
        filtros=json.dumps({"estatus": "A", "usuario_id": current_user.id}),
        titulo="Mis Requisiciones",
        estatus="A",
    )


@req_requisiciones.route("/req_requisiciones/inactivos")
@permission_required(MODULO, Permiso.MODIFICAR)
def list_inactive():
    """Listado de Requisiciones inactivas"""
    return render_template(
        "req_requisiciones/list.jinja2",
        filtros=json.dumps({"estatus": "B"}),
        titulo="Listado de requisiciones inactivas",
        estatus="B",
    )


@req_requisiciones.route("/req_requisiciones/nuevo", methods=["GET", "POST"])
@permission_required(MODULO, Permiso.CREAR)
def new():
    """Requisiciones nueva"""
    form = ReqRequisicionNewForm()
    # form.area.choices = [("", "")] + [(a.id, a.descripcion) for a in Autoridad.query.order_by("descripcion")]
    form.codigoTmp.choices = [("", "")] + [
        (c.id, c.codigo + " - " + c.descripcion) for c in ReqCatalogo.query.order_by("descripcion")
    ]
    form.claveTmp.choices = (
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
            # autoridad_id=form.area.data,
            estado="BORRADOR",
            observaciones=safe_string(form.observaciones.data, max_len=256, to_uppercase=True, save_enie=True),
            justificacion=safe_string(form.justificacion.data, max_len=1024, to_uppercase=True, save_enie=True),
            fecha=datetime.now(),
            gasto=safe_string(form.gasto.data, to_uppercase=True, save_enie=True),
            glosa=form.glosa.data,
            programa=safe_string(form.programa.data, to_uppercase=True, save_enie=True),
            fuente_financiamiento=safe_string(form.fuenteFinanciamiento.data, to_uppercase=True, save_enie=True),
            area_final=safe_string(form.areaFinal.data, to_uppercase=True, save_enie=True),
            fecha_requerida=form.fechaRequerida.data,
            autoridad_id=current_user.autoridad_id,
            solicito_id=0,
            autorizo_id=0,
            reviso_id=0,
        )
        req_requisicion.save()
        # Guardar los registros de la requisición
        for registros in form.articulos:
            if registros.codigo.data != "":

                req_requisicion_registro = ReqRequisicionRegistro(
                    req_requisicion_id=req_requisicion.id,
                    req_catalogo_id=registros.idArticulo.data,
                    clave=registros.clave.data,
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
        "req_requisiciones/new.jinja2", titulo="Requisicion nueva", form=form, area=current_user.autoridad.descripcion
    )


@req_requisiciones.route("/req_requisiciones/editar/<req_requisicion_id>", methods=["GET", "POST"])
@permission_required(MODULO, Permiso.CREAR)
def edit(req_requisicion_id):
    """Requisiciones editar"""

    # Consultar la requisicion
    req_requisicion = ReqRequisicion.query.get_or_404(req_requisicion_id)
    # Consultar los articulos de la requisicion
    articulos = (
        ReqRequisicionRegistro.query.filter_by(req_requisicion_id=req_requisicion_id, estatus="A").join(ReqCatalogo).all()
    )

    # Validar que el estatus sea A
    if req_requisicion.estatus != "A":
        flash("No puede editar esta requisición porque esta eliminada", "warning")
        return redirect(url_for("req_requisiciones.detail", req_requisicion_id=req_requisicion_id))

    # Validar que el estado sea CREADO
    if req_requisicion.estado != "BORRADOR":
        flash("No puede editar esta requisición porque ya fue enviada a revisión (el estado no es CREADO)", "warning")
        return redirect(url_for("req_requisiciones.detail", req_requisicion_id=req_requisicion_id))

    # Validar que el usuario sea quien creo la requisición
    if not (current_user.can_admin(MODULO) or req_requisicion.usuario_id == current_user.id):
        flash("No puede editar esta requisición porque usted no la creo", "warning")
        return redirect(url_for("req_requisiciones.detail", req_requisicion_id=req_requisicion_id))

    form = ReqRequisicionNewForm()
    # form.area.choices = [("", "")] + [(a.id, a.descripcion) for a in Autoridad.query.order_by("descripcion")]
    form.codigoTmp.choices = [("", "")] + [
        (c.id, c.codigo + " - " + c.descripcion) for c in ReqCatalogo.query.order_by("descripcion")
    ]
    form.claveTmp.choices = (
        [("", "")]
        + [("INS", "INSUFICIENCIA")]
        + [("REP", "REPOSICION DE BIENES")]
        + [("OBS", "OBSOLESENCIA")]
        + [("AMP", "AMPLIACION COBERTURA DEL SERVICIO")]
        + [("NUE", "NUEVO PROYECTO")]
    )

    if form.validate_on_submit():
        # Guardar requisicion

        req_requisicion.observaciones = (safe_string(form.observaciones.data, max_len=256, to_uppercase=True, save_enie=True),)
        req_requisicion.justificacion = (safe_string(form.justificacion.data, max_len=1024, to_uppercase=True, save_enie=True),)
        req_requisicion.gasto = (safe_string(form.gasto.data, to_uppercase=True, save_enie=True),)
        req_requisicion.glosa = (form.glosa.data,)
        req_requisicion.programa = (safe_string(form.programa.data, to_uppercase=True, save_enie=True),)
        req_requisicion.fuente_financiamiento = (
            safe_string(form.fuenteFinanciamiento.data, to_uppercase=True, save_enie=True),
        )
        req_requisicion.fecha_requerida = (form.fechaRequerida.data,)

        req_requisicion.save()
        # Eliminar los articulos registrados antes de la edicion
        for registro_a_eliminar in articulos:
            articulo = ReqRequisicionRegistro.query.filter_by(id=registro_a_eliminar.id).first()
            if articulo:
                articulo.estatus = "B"
                articulo.save()

        # Guardar los registros de la requisición
        for registros in form.articulos:
            if registros.codigo.data != "":

                req_requisicion_registro = ReqRequisicionRegistro(
                    req_requisicion_id=req_requisicion.id,
                    req_catalogo_id=registros.idArticulo.data,
                    clave=registros.clave.data,
                    cantidad=registros.cantidad.data,
                    detalle=registros.detalle.data,
                )
                req_requisicion_registro.save()

        # Guardar en la bitacora
        bitacora = Bitacora(
            modulo=Modulo.query.filter_by(nombre=MODULO).first(),
            usuario=current_user,
            descripcion=safe_message(f"Requisicion actualizada: {req_requisicion.gasto}"),
            url=url_for("req_requisiciones.detail", req_requisicion_id=req_requisicion.id),
        )
        bitacora.save()
        flash(bitacora.descripcion, "success")
        return redirect(bitacora.url)

    form.fecha.data = req_requisicion.fecha
    form.gasto.data = req_requisicion.gasto
    form.glosa.data = req_requisicion.glosa
    form.programa.data = req_requisicion.programa
    form.fuenteFinanciamiento.data = req_requisicion.fuente_financiamiento
    form.fechaRequerida.data = req_requisicion.fecha_requerida
    form.areaFinal.data = req_requisicion.area_final
    form.observaciones.data = req_requisicion.observaciones
    form.justificacion.data = req_requisicion.justificacion

    # consulta previa para obtener los articulos registrados en la requisicion
    # articulos = ReqRequisicionRegistro.query.filter_by(req_requisicion_id=req_requisicion_id).join(ReqCatalogo).all()
    x = 0
    for registro in articulos:
        form.articulos[x].idArticulo.data = registro.req_catalogo.id
        form.articulos[x].codigo.data = registro.req_catalogo.codigo
        form.articulos[x].descripcion.data = registro.req_catalogo.descripcion
        form.articulos[x].unidad.data = registro.req_catalogo.unidad_medida
        form.articulos[x].clave.data = registro.clave
        form.articulos[x].cantidad.data = registro.cantidad
        form.articulos[x].detalle.data = registro.detalle

        x = x + 1

    return render_template(
        "req_requisiciones/edit.jinja2",
        titulo="Editar Requisicion",
        form=form,
        area=current_user.autoridad.descripcion,
        req_requisicion_registro=articulos,
        req_requisicion=req_requisicion,
    )


@req_requisiciones.route("/req_requisiciones/<req_requisicion_id>")
def detail(req_requisicion_id):
    """Detalle de una Requisicion"""
    current_user_roles = current_user.get_roles()
    # Si es asistente, mostrar TODAS las Requisiciones de su oficina
    req_requisicion = ReqRequisicion.query.get_or_404(req_requisicion_id)
    articulos = (
        ReqRequisicionRegistro.query.filter_by(req_requisicion_id=req_requisicion_id, estatus="A").join(ReqCatalogo).all()
    )
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
    # return {'descripcion':'nombre del articulo', 'unidad_medida':'Paquete'}


@req_requisiciones.route("/req_requisiciones/<req_requisicion_id>/solicitar", methods=["GET", "POST"])
@permission_required(MODULO, Permiso.MODIFICAR)
def step_2_request(req_requisicion_id):
    """Formulario Requisiciones (step 2 request) Solicitar"""
    req_requisicion = ReqRequisicion.query.get_or_404(req_requisicion_id)
    puede_firmarlo = True
    # Validar que sea activo
    if req_requisicion.estatus != "A":
        flash("La Requisición esta eliminada", "warning")
        puede_firmarlo = False
    # Validar el estado
    if req_requisicion.estado != "BORRADOR":
        flash("La Requisición no esta en estado BORRADOR", "warning")
        puede_firmarlo = False
    # Validar roles
    if ROL_SOLICITANTES not in current_user.get_roles():
        flash("Usted no tiene el rol para solicitar una requisición", "warning")
        puede_firmarlo = False
    # Si no puede solicitarla, redireccionar a la pagina de detalle
    if not puede_firmarlo:
        return redirect(url_for("req_requisiciones.detail", req_requisicion_id=req_requisicion_id))
    # Si viene el formulario
    if puede_firmarlo:
        req_requisicion.solicito_id = current_user.id
        req_requisicion.solicito_tiempo = datetime.now()
        req_requisicion.firma_simple = ReqRequisicion.elaborar_hash(req_requisicion)
        req_requisicion.estado = "SOLICITADO"
        req_requisicion.save()

        bitacora = Bitacora(
            modulo=Modulo.query.filter_by(nombre=MODULO).first(),
            usuario=current_user,
            descripcion=safe_message(f"Firmado simple de la Requisición {req_requisicion.gasto}"),
            url=url_for("req_requisiciones.detail", req_requisicion_id=req_requisicion.id),
        )
        bitacora.save()
        # Agregar registro a la bitácora
        flash(bitacora.descripcion, "success")

    return render_template("req_requisiciones/step_2_request.jinja2", req_requisicion=req_requisicion)


@req_requisiciones.route("/req_requisiciones/<req_requisicion_id>/cancelar_solicitado", methods=["GET", "POST"])
@permission_required(MODULO, Permiso.MODIFICAR)
def cancel_2_request(req_requisicion_id):
    """Formulario Requisicion (cancel 2 request) Cancelar solicitado"""
    req_requisicion = ReqRequisicion.query.get_or_404(req_requisicion_id)
    puede_cancelarlo = True
    # Validar que sea activo
    if req_requisicion.estatus != "A":
        flash("La requisición esta cancelada", "warning")
        puede_cancelarlo = False
    # Validar el estado
    if req_requisicion.estado != "SOLICITADO":
        flash("La requisición no esta en estado SOLICITADO", "warning")
        puede_cancelarlo = False
    # Validar roles
    if ROL_SOLICITANTES not in current_user.get_roles():
        flash("Usted no tiene el rol para cancelar un una requisición solicitada", "warning")
        puede_cancelarlo = False
    # Si no puede cancelarlo, redireccionar a la pagina de detalle
    if not puede_cancelarlo:
        return redirect(url_for("req_requisiciones.detail", req_requisicion_id=req_requisicion_id))
    # Si puede cancelarlo
    if puede_cancelarlo:
        req_requisicion.estado = "CANCELADO POR SOLICITANTE"
        req_requisicion.esta_cancelado = 1
        req_requisicion.save()

    return redirect(url_for("req_requisiciones.detail", req_requisicion_id=req_requisicion_id))


@req_requisiciones.route("/req_requisiciones/<req_requisicion_id>/autorizar", methods=["GET", "POST"])
@permission_required(MODULO, Permiso.MODIFICAR)
def step_3_authorize(req_requisicion_id):
    """Formulario Requisiciones (step 3 authorize) Autorizar"""
    req_requisicion = ReqRequisicion.query.get_or_404(req_requisicion_id)
    puede_firmarlo = True
    # Validar que sea activo
    if req_requisicion.estatus != "A":
        flash("La Requisición esta eliminada", "warning")
        puede_firmarlo = False
    # Validar el estado
    if req_requisicion.estado != "SOLICITADO":
        flash("La Requisición no esta en estado SOLICITADO", "warning")
        puede_firmarlo = False
    # Validar roles
    if ROL_AUTORIZANTES not in current_user.get_roles():
        flash("Usted no tiene el rol para AUTORIZAR una requisición", "warning")
        puede_firmarlo = False
    # Si no puede autorizarla, redireccionar a la pagina de detalle
    if not puede_firmarlo:
        return redirect(url_for("req_requisiciones.detail", req_requisicion_id=req_requisicion_id))
    # Si viene el formulario

    if puede_firmarlo:
        req_requisicion.autorizo_id = current_user.id
        req_requisicion.autorizo_tiempo = datetime.now()
        req_requisicion.estado = "AUTORIZADO"
        req_requisicion.save()

        bitacora = Bitacora(
            modulo=Modulo.query.filter_by(nombre=MODULO).first(),
            usuario=current_user,
            descripcion=safe_message(f"Autorizado de la Requisición {req_requisicion.gasto}"),
            url=url_for("req_requisiciones.detail", req_requisicion_id=req_requisicion.id),
        )
        bitacora.save()
        # Agregar registro a la bitácora
        flash(bitacora.descripcion, "success")

    return render_template("req_requisiciones/step_3_authorize.jinja2", req_requisicion=req_requisicion)


@req_requisiciones.route("/req_requisiciones/<req_requisicion_id>/cancelar_autorizado", methods=["GET", "POST"])
@permission_required(MODULO, Permiso.MODIFICAR)
def cancel_3_authorize(req_requisicion_id):
    """Formulario Requisicion (cancel 3 authorize) Cancelar autorizado"""
    req_requisicion = ReqRequisicion.query.get_or_404(req_requisicion_id)
    puede_cancelarlo = True
    # Validar que sea activo
    if req_requisicion.estatus != "A":
        flash("La requisición esta cancelada", "warning")
        puede_cancelarlo = False
    # Validar el estado
    if req_requisicion.estado != "AUTORIZADO":
        flash("La requisición no esta en estado autorizado", "warning")
        puede_cancelarlo = False
    # Validar roles
    if ROL_AUTORIZANTES not in current_user.get_roles():
        flash("Usted no tiene el rol para cancelar un una requisición autorizada", "warning")
        puede_cancelarlo = False
    if req_requisicion.solicito_email != current_user.email:
        flash("Usted no es el autorizante de esta requisición", "warning")
        puede_cancelarlo = False
    # Si no puede cancelarlo, redireccionar a la pagina de detalle
    if not puede_cancelarlo:
        return redirect(url_for("req_requisiciones.detail", req_requisicion_id=req_requisicion_id))
    # Si viene el formulario
    form = ReqRequisicionCancel3AuthorizeForm()
    if form.validate_on_submit():
        # Crear la tarea en el fondo
        tarea = current_user.launch_task(
            comando="req_requisiciones.tasks.cancelar_autorizar",
            mensaje="Elaborando solicitud en motor de firma electronica",
            req_requisicion_id=req_requisicion.id,
            contrasena=form.contrasena.data,
            motivo=form.motivo.data,
        )
        flash(f"{tarea.mensaje} Esta página se va a recargar en 10 segundos...", "info")
        return redirect(url_for("req_requisiciones.detail", req_requisicion_id=req_requisicion_id))
    # Mostrar formulario
    form.autorizo_nombre.data = current_user.nombre
    form.autorizo_puesto.data = current_user.puesto
    form.autorizo_email.data = current_user.email
    return render_template("req_requisiciones/cancel_3_authorize.jinja2", form=form, req_requisicion=req_requisicion)


@req_requisiciones.route("/req_requisiciones/<req_requisicion_id>/revisar", methods=["GET", "POST"])
@permission_required(MODULO, Permiso.MODIFICAR)
def step_4_review(req_requisicion_id):
    """Formulario Requisiciones (step 4 review) Revisar"""
    req_requisicion = ReqRequisicion.query.get_or_404(req_requisicion_id)
    puede_firmarlo = True
    # Validar que sea activo
    if req_requisicion.estatus != "A":
        flash("La Requisición esta eliminada", "warning")
        puede_firmarlo = False
    # Validar el estado
    if req_requisicion.estado != "AUTORIZADO":
        flash("La Requisición no esta en estado AUTORIZADO", "warning")
        puede_firmarlo = False
    # Validar roles
    if ROL_REVISANTES not in current_user.get_roles():
        flash("Usted no tiene el rol para REVISAR una requisición", "warning")
        puede_firmarlo = False
    # Si no puede revisar la requisición, redireccionar a la pagina de detalle
    if not puede_firmarlo:
        return redirect(url_for("req_requisiciones.detail", req_requisicion_id=req_requisicion_id))

    # si puede firmarlo
    if puede_firmarlo:
        req_requisicion.reviso_id = current_user.id
        req_requisicion.reviso_tiempo = datetime.now()
        req_requisicion.estado = "REVISADO"
        req_requisicion.save()

        bitacora = Bitacora(
            modulo=Modulo.query.filter_by(nombre=MODULO).first(),
            usuario=current_user,
            descripcion=safe_message(f"Revisado de la Requisición {req_requisicion.gasto}"),
            url=url_for("req_requisiciones.detail", req_requisicion_id=req_requisicion.id),
        )
        bitacora.save()
        # Agregar registro a la bitácora
        flash(bitacora.descripcion, "success")

    return render_template("req_requisiciones/step_4_review.jinja2", req_requisicion=req_requisicion)


@req_requisiciones.route("/req_requisiciones/<req_requisicion_id>/cancelar_revisado", methods=["GET", "POST"])
@permission_required(MODULO, Permiso.MODIFICAR)
def cancel_4_review(req_requisicion_id):
    """Formulario Requisicion (cancel 4 review) Cancelar revisado"""
    req_requisicion = ReqRequisicion.query.get_or_404(req_requisicion_id)
    puede_cancelarlo = True
    # Validar que sea activo
    if req_requisicion.estatus != "A":
        flash("La requisición esta cancelada", "warning")
        puede_cancelarlo = False
    # Validar el estado
    if req_requisicion.estado != "REVISADO":
        flash("La requisición no esta en estado revisado", "warning")
        puede_cancelarlo = False
    # Validar roles
    if ROL_REVISANTES not in current_user.get_roles():
        flash("Usted no tiene el rol para cancelar un una requisición revisada", "warning")
        puede_cancelarlo = False
    if req_requisicion.reviso_email != current_user.email:
        flash("Usted no es el revisante de esta requisición", "warning")
        puede_cancelarlo = False
    # Si no puede cancelarlo, redireccionar a la pagina de detalle
    if not puede_cancelarlo:
        return redirect(url_for("req_requisiciones.detail", req_requisicion_id=req_requisicion_id))
    # Si viene el formulario
    form = ReqRequisicionCancel4ReviewForm()
    if form.validate_on_submit():
        # Crear la tarea en el fondo
        tarea = current_user.launch_task(
            comando="req_requisiciones.tasks.cancelar_revisar",
            mensaje="Elaborando solicitud en motor de firma electronica",
            req_requisicion_id=req_requisicion.id,
            contrasena=form.contrasena.data,
            motivo=form.motivo.data,
        )
        flash(f"{tarea.mensaje} Esta página se va a recargar en 10 segundos...", "info")
        return redirect(url_for("req_requisiciones.detail", req_requisicion_id=req_requisicion_id))
    # Mostrar formulario
    form.reviso_nombre.data = current_user.nombre
    form.reviso_puesto.data = current_user.puesto
    form.reviso_email.data = current_user.email
    return render_template("req_requisiciones/cancel_4_review.jinja2", form=form, req_requisicion=req_requisicion)


@req_requisiciones.route("/req_requisiciones/<req_requisicion_id>/imprimir")
def detail_print(req_requisicion_id):
    """Impresion de la Requsición"""

    # Consultar la requisición
    req_requisicion = ReqRequisicion.query.get_or_404(req_requisicion_id)
    articulos = (
        database.session.query(ReqRequisicionRegistro, ReqCatalogo)
        .filter_by(req_requisicion_id=req_requisicion_id, estatus="A")
        .join(ReqCatalogo)
        .all()
    )
    usuario = Usuario.query.get_or_404(req_requisicion.usuario_id)
    usuario_solicito = Usuario.query.get_or_404(req_requisicion.solicito_id) if req_requisicion.solicito_id > 0 else ""
    usuario_autorizo = Usuario.query.get_or_404(req_requisicion.autorizo_id) if req_requisicion.autorizo_id > 0 else ""
    usuario_reviso = Usuario.query.get_or_404(req_requisicion.reviso_id) if req_requisicion.reviso_id > 0 else ""
    autoridad = Autoridad.query.get_or_404(req_requisicion.usuario.autoridad_id)

    # Validar que pueda verla
    puede_imprimirlo = False

    # Si es administrador, puede imprimirla
    if current_user.can_admin(MODULO):
        puede_imprimirlo = True

    # Si tiene uno de los roles que pueden imprimir y esta activo, puede imprimirla
    if set(current_user.get_roles()).intersection(ROLES_PUEDEN_IMPRIMIR) and req_requisicion.estatus == "A":
        puede_imprimirlo = True

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

    # Si tiene uno de los roles que pueden imprimir y esta activo, puede imprimirla
    if set(current_user.get_roles()).intersection(ROLES_PUEDEN_IMPRIMIR) and req_requisicion.estatus == "A":
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


@req_requisiciones.route("/req_requisiciones/obtener_archivo_pdf_url_json/<req_requisicion_id>", methods=["GET", "POST"])
def get_file_pdf_url_json(req_requisicion_id):
    """Obtener el URL del archivo PDF en formato JSON, para usar en el botón de descarga"""
    # Consultar el oficio
    req_requisicion_id = safe_uuid(req_requisicion_id)
    if not req_requisicion_id:
        return {
            "success": False,
            "message": "ID de oficio inválido",
        }
    req_requisicion = ReqRequisicion.query.get_or_404(req_requisicion_id)
    # Validar el estatus, que no esté eliminado
    if req_requisicion.estatus != "A":
        return {
            "success": False,
            "message": "La requisición está eliminado",
        }
    # Validar que tenga el estado FIRMADO o ENVIADO
    # if req_requisicion.estado not in ["FIRMADO", "ENVIADO"]:
    #     return {
    #         "success": False,
    #         "message": "La requisición no está en estado FIRMADO o ENVIADO, no se puede descargar",
    #     }
    # Validar que tenga archivo_pdf_url
    if req_requisicion.archivo_pdf_url is None or req_requisicion.archivo_pdf_url == "":
        return {
            "success": False,
            "message": "La requisición no tiene archivo PDF, no se puede descargar. Refresque la página nuevamente.",
        }
    # Entregar el URL del archivo PDF
    return {
        "success": True,
        "message": "Archivo PDF disponible",
        "url": url_for("req_requisiciones.download_file_pdf", req_requisicion_id=req_requisicion.id),
    }


@req_requisiciones.route("/req_requisiciones/descargar_archivo_pdf/<req_requisicion_id>")
def download_file_pdf(req_requisicion_id):
    """Descargar archivo PDF"""
    # Consultar la requisición
    req_requisicion_id = safe_uuid(req_requisicion_id)
    if not req_requisicion_id:
        flash("ID de requisición inválido", "warning")
        return redirect(url_for("req_requisiciones.list_active"))
    req_requisicion = ReqRequisicion.query.get_or_404(req_requisicion_id)
    # Validar el estatus, que no esté eliminado
    if req_requisicion.estatus != "A":
        flash("La requisición está eliminado", "warning")
        return redirect(url_for("req_requisiciones.detail", req_requisicion_id=req_requisicion.id))
    # Validar que tenga el estado FIRMADO o ENVIADO
    # if req_requisicion.estado not in ["FIRMADO", "ENVIADO"]:
    #     flash("La requisición no está en estado FIRMADO o ENVIADO, no se puede descargar", "warning")
    #     return redirect(url_for("req_requisiciones.detail", req_requisicion_id=req_requisicion.id))
    # Validar que tenga archivo_pdf_url
    if req_requisicion.archivo_pdf_url is None or req_requisicion.archivo_pdf_url == "":
        flash("La requisición no tiene archivo PDF, no se puede descargar", "warning")
        return redirect(url_for("req_requisiciones.detail", req_requisicion_id=req_requisicion.id))
    # Obtener el contenido del archivo
    try:
        archivo = get_file_from_gcs(
            bucket_name=current_app.config["CLOUD_STORAGE_DEPOSITO_OFICIOS"],
            blob_name=get_blob_name_from_url(req_requisicion.archivo_pdf_url),
        )
    except (MyBucketNotFoundError, MyFileNotFoundError, MyNotValidParamError) as error:
        raise NotFound("No se encontró el archivo.")
    # Entregar el archivo PDF
    response = make_response(archivo)
    response.headers["Content-Type"] = "application/pdf"
    response.headers["Content-Disposition"] = f"attachment; filename={req_requisicion.folio}.pdf"
    return response


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
