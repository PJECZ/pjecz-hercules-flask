"""
Ofi Documentos, vistas
"""

from datetime import datetime
import json

from flask import Blueprint, current_app, flash, redirect, render_template, request, url_for
from flask_login import current_user, login_required

from lib.datatables import get_datatable_parameters, output_datatable_json
from lib.folio import validar_folio
from lib.safe_string import safe_string, safe_message, safe_clave
from hercules.extensions import database
from hercules.blueprints.bitacoras.models import Bitacora
from hercules.blueprints.modulos.models import Modulo
from hercules.blueprints.permisos.models import Permiso
from hercules.blueprints.usuarios.decorators import permission_required
from hercules.blueprints.ofi_documentos.models import OfiDocumento
from hercules.blueprints.ofi_documentos.forms import OfiDocumentoNewForm, OfiDocumentoEditForm, OfiDocumentoSignForm
from hercules.blueprints.ofi_plantillas.models import OfiPlantilla
from hercules.blueprints.usuarios.models import Usuario
from hercules.blueprints.autoridades.models import Autoridad
from hercules.blueprints.ofi_documentos_destinatarios.models import OfiDocumentoDestinatario

DIAS_VENCIMIENTO_ADVERTENCIA = -3
DIAS_VENCIMIENTO_EMERGENCIA = -1

MODULO = "OFI DOCUMENTOS"

ofi_documentos = Blueprint("ofi_documentos", __name__, template_folder="templates")


@ofi_documentos.before_request
@login_required
@permission_required(MODULO, Permiso.VER)
def before_request():
    """Permiso por defecto"""


@ofi_documentos.route("/ofi_documentos/datatable_json", methods=["GET", "POST"])
def datatable_json():
    """DataTable JSON para listado de Ofi Documentos"""
    # Tomar parámetros de Datatables
    draw, start, rows_per_page = get_datatable_parameters()
    # Consultar
    consulta = OfiDocumento.query
    # Primero filtrar por columnas propias
    if "estatus" in request.form:
        consulta = consulta.filter(OfiDocumento.estatus == request.form["estatus"])
    else:
        consulta = consulta.filter(OfiDocumento.estatus == "A")
    if "usuario_id" in request.form:
        consulta = consulta.filter(OfiDocumento.usuario_id == request.form["usuario_id"])
    if "estado" in request.form:
        consulta = consulta.filter(OfiDocumento.estado == request.form["estado"])
    if "folio" in request.form:
        folio = request.form["folio"]
        consulta = consulta.filter(OfiDocumento.folio.contains(folio))
    if "descripcion" in request.form:
        descripcion = safe_string(request.form["descripcion"])
        if descripcion:
            consulta = consulta.filter(OfiDocumento.descripcion.contains(descripcion))
    # Luego filtrar por columnas de otras tablas
    tabla_usuario_incluida = False
    if "autor" in request.form:
        if tabla_usuario_incluida is False:
            consulta = consulta.join(Usuario)
            tabla_usuario_incluida = True
        autor = request.form["autor"].lower()
        consulta = consulta.filter(Usuario.email.contains(autor))
    if "autoridad" in request.form:
        autoridad = safe_clave(request.form["autoridad"])
        if autoridad:
            if tabla_usuario_incluida is False:
                consulta = consulta.join(Usuario)
                tabla_usuario_incluida = True
            consulta = consulta.join(Autoridad, Usuario.autoridad_id == Autoridad.id)
            consulta = consulta.filter(Autoridad.clave.contains(autoridad))
    if "usuario_autoridad_id" in request.form:
        if tabla_usuario_incluida is False:
            consulta = consulta.join(Usuario)
            tabla_usuario_incluida = True
        consulta = consulta.filter(Usuario.autoridad_id == request.form["usuario_autoridad_id"])
    if "usuario_destinatario_id" in request.form:
        consulta = consulta.join(OfiDocumentoDestinatario, OfiDocumentoDestinatario.ofi_documento_id == OfiDocumento.id)
        consulta = consulta.filter(OfiDocumentoDestinatario.usuario_id == request.form["usuario_destinatario_id"])
        consulta = consulta.filter(OfiDocumentoDestinatario.estatus == "A")
    # Ordenar y paginar
    registros = consulta.order_by(OfiDocumento.id.desc()).offset(start).limit(rows_per_page).all()
    total = consulta.count()
    # Elaborar datos para DataTable
    data = []
    for resultado in registros:
        # Formar campo de vencimiento
        vencimiento_fecha = resultado.vencimiento_fecha.strftime("%Y-%m-%d") if resultado.vencimiento_fecha else "-"
        vencimiento_icono = ""
        dias_vencimiento = ""
        if resultado.vencimiento_fecha is not None:
            dias_vencimiento = (datetime.now().date() - resultado.vencimiento_fecha).days
            if DIAS_VENCIMIENTO_EMERGENCIA <= dias_vencimiento <= 0:
                vencimiento_icono = "🚨"
            if DIAS_VENCIMIENTO_ADVERTENCIA <= dias_vencimiento < DIAS_VENCIMIENTO_EMERGENCIA:
                vencimiento_icono = "⚠️"
        vencimiento = f"{vencimiento_fecha} {vencimiento_icono}"
        # Elaborar registro
        data.append(
            {
                "detalle": {
                    "id": resultado.id,
                    "url": url_for("ofi_documentos.detail", ofi_documento_id=resultado.id),
                },
                "autor": {
                    "email": resultado.usuario.email,
                    "nombre": resultado.usuario.nombre,
                    "url": url_for("usuarios.detail", usuario_id=resultado.usuario.id),
                },
                "autoridad": {
                    "clave": resultado.usuario.autoridad.clave,
                    "nombre": resultado.usuario.autoridad.descripcion_corta,
                    "url": (
                        url_for("autoridades.detail", autoridad_id=resultado.usuario.autoridad.id)
                        if current_user.can_view("AUTORIDADES")
                        else ""
                    ),
                },
                "folio": resultado.folio,
                "vencimiento": vencimiento,
                "descripcion": resultado.descripcion,
                "creado": resultado.creado.strftime("%Y-%m-%d %H:%M"),
                "estado": resultado.estado,
                "cancelado": resultado.esta_cancelado,
            }
        )
    # Entregar JSON
    return output_datatable_json(draw, total, data)


@ofi_documentos.route("/ofi_documentos")
def list_active():
    """Listado de Ofi Documentos activos"""
    return list_active_mis_oficios()


@ofi_documentos.route("/ofi_documentos/mis_oficios")
def list_active_mis_oficios():
    """Listado de Ofi Documentos activos"""
    return render_template(
        "ofi_documentos/list.jinja2",
        filtros=json.dumps({"estatus": "A", "usuario_id": current_user.id}),
        titulo="Mis Oficios",
        estatus="A",
        estados=OfiDocumento.ESTADOS,
    )


@ofi_documentos.route("/ofi_documentos/mi_bandeja_entrada")
def list_active_mi_bandeja_entrada():
    """Listado de Ofi Documentos donde el usuario es destinatario"""
    return render_template(
        "ofi_documentos/list.jinja2",
        filtros=json.dumps({"estatus": "A", "estado": "ENVIADO", "usuario_destinatario_id": current_user.id}),
        titulo="Mi Bandeja de Entrada",
        estatus="A",
        estados=OfiDocumento.ESTADOS,
    )


@ofi_documentos.route("/ofi_documentos/mi_autoridad")
def list_active_mi_autoridad():
    """Listado de Ofi Documentos de la autoridad del usuario"""
    return render_template(
        "ofi_documentos/list.jinja2",
        filtros=json.dumps({"estatus": "A", "usuario_autoridad_id": current_user.autoridad.id}),
        titulo="Mi Autoridad",
        estatus="A",
        estados=OfiDocumento.ESTADOS,
    )


@ofi_documentos.route("/ofi_documentos/mis_oficios/inactivos")
@permission_required(MODULO, Permiso.ADMINISTRAR)
def list_inactive():
    """Listado de Ofi Documentos inactivos"""
    return render_template(
        "ofi_documentos/list.jinja2",
        filtros=json.dumps({"estatus": "B", "usuario_id": current_user.id}),
        titulo="Mis Oficios inactivos",
        estatus="B",
        estados=OfiDocumento.ESTADOS,
    )


@ofi_documentos.route("/ofi_documentos/<int:ofi_documento_id>")
def detail(ofi_documento_id):
    """Detalle de un Ofi-Documento"""
    ofi_documento = OfiDocumento.query.get_or_404(ofi_documento_id)
    mostrar_boton_responder = False
    # Consultar el usuario firmante, si lo tiene
    usuario_firmante = None
    if ofi_documento.firma_simple_usuario_id is not None:
        usuario_firmante = Usuario.query.get(ofi_documento.firma_simple_usuario_id)
    # Si el usuario que lo ve es un Destinatario, se va a marcar como leído
    if ofi_documento.estado == "ENVIADO":
        # Buscar al usuario entre los destinatarios
        usuario_destinatario = (
            OfiDocumentoDestinatario.query.filter_by(ofi_documento_id=ofi_documento.id)
            .filter_by(usuario_id=current_user.id)
            .first()
        )
        # Marcar como leído si es que no lo ha sido
        if usuario_destinatario is not None and usuario_destinatario.fue_leido is False:
            usuario_destinatario.fue_leido = True
            usuario_destinatario.fue_leido_tiempo = datetime.now()
            usuario_destinatario.save()
        if usuario_destinatario is not None:
            mostrar_boton_responder = True
    # Para mostrar el contenido del documento, se usa Syncfusion Document Editor con un formulario que NO se envía
    form = OfiDocumentoNewForm()
    form.descripcion.data = ofi_documento.descripcion
    form.contenido_sfdt.data = ofi_documento.contenido_sfdt
    # Entregar
    return render_template(
        "ofi_documentos/detail.jinja2",
        ofi_documento=ofi_documento,
        usuario_firmante=usuario_firmante,
        form=form,
        syncfusion_license_key=current_app.config["SYNCFUSION_LICENSE_KEY"],
        mostrar_boton_responder=mostrar_boton_responder,
    )


@ofi_documentos.route("/ofi_documentos/nuevo/<int:ofi_plantilla_id>", methods=["GET", "POST"])
@permission_required(MODULO, Permiso.CREAR)
def new(ofi_plantilla_id):
    """Nuevo Ofi Documento"""
    ofi_plantilla = OfiPlantilla.query.get_or_404(ofi_plantilla_id)
    form = OfiDocumentoNewForm()
    if form.validate_on_submit():
        es_valido = True
        # Validar el folio, separar el número y el año
        folio = form.folio.data.strip()
        numero_folio = None
        anio_folio = None
        if folio != "":
            try:
                numero_folio, anio_folio = validar_folio(folio)
            except ValueError as error:
                flash(str(error), "warning")
                es_valido = False
        # Validar la fecha de vencimiento
        vencimiento_fecha = form.vencimiento_fecha.data
        if vencimiento_fecha is not None and vencimiento_fecha < datetime.now().date():
            flash("La fecha de vencimiento no puede ser anterior a la fecha actual", "warning")
            es_valido = False
        if es_valido:
            ofi_documento = OfiDocumento(
                usuario=current_user,
                descripcion=safe_string(form.descripcion.data, save_enie=True),
                folio=folio,
                folio_anio=anio_folio,
                folio_num=numero_folio,
                vencimiento_fecha=vencimiento_fecha,
                contenido_sfdt=form.contenido_sfdt.data.strip(),
                estado="BORRADOR",
                cadena_oficio_id=form.cadena_oficio_id.data if form.cadena_oficio_id.data else None,
            )
            ofi_documento.save()
            bitacora = Bitacora(
                modulo=Modulo.query.filter_by(nombre=MODULO).first(),
                usuario=current_user,
                descripcion=safe_message(f"Nuevo Oficio Documento {ofi_documento.descripcion}"),
                url=url_for("ofi_documentos.detail", ofi_documento_id=ofi_documento.id),
            )
            bitacora.save()
            flash(bitacora.descripcion, "success")
            return redirect(bitacora.url)
    # Cargar los datos de la plantilla en el formulario
    form.descripcion.data = ofi_plantilla.descripcion
    form.contenido_sfdt.data = ofi_plantilla.contenido_sfdt
    # Entregar
    return render_template(
        "ofi_documentos/new_syncfusion_document.jinja2",
        form=form,
        syncfusion_license_key=current_app.config["SYNCFUSION_LICENSE_KEY"],
        ofi_plantilla_id=ofi_plantilla_id,
    )


@ofi_documentos.route("/ofi_documentos/edicion/<int:ofi_documento_id>", methods=["GET", "POST"])
@permission_required(MODULO, Permiso.MODIFICAR)
def edit(ofi_documento_id):
    """Editar Ofi Documento"""
    ofi_documento = OfiDocumento.query.get_or_404(ofi_documento_id)
    form = OfiDocumentoEditForm()
    if form.validate_on_submit():
        es_valido = True
        # Validar el folio, separar el número y el año
        folio = form.folio.data.strip()
        numero_folio = None
        anio_folio = None
        if folio != "":
            try:
                numero_folio, anio_folio = validar_folio(folio)
            except ValueError as error:
                flash(str(error), "warning")
                es_valido = False
        # Validar la fecha de vencimiento
        vencimiento_fecha = form.vencimiento_fecha.data
        if vencimiento_fecha is not None and vencimiento_fecha < datetime.now().date():
            flash("La fecha de vencimiento no puede ser anterior a la fecha actual", "warning")
            es_valido = False
        if es_valido:
            ofi_documento.descripcion = safe_string(form.descripcion.data, save_enie=True)
            ofi_documento.folio = folio
            ofi_documento.folio_anio = anio_folio
            ofi_documento.folio_num = numero_folio
            ofi_documento.vencimiento_fecha = vencimiento_fecha
            ofi_documento.contenido_sfdt = form.contenido_sfdt.data.strip()
            ofi_documento.save()
            bitacora = Bitacora(
                modulo=Modulo.query.filter_by(nombre=MODULO).first(),
                usuario=current_user,
                descripcion=safe_message(f"Editado Oficio Documento {ofi_documento.descripcion}"),
                url=url_for("ofi_documentos.detail", ofi_documento_id=ofi_documento.id),
            )
            bitacora.save()
            flash(bitacora.descripcion, "success")
            return redirect(bitacora.url)
    # Cargar los datos en el formulario
    form.descripcion.data = ofi_documento.descripcion
    form.folio.data = ofi_documento.folio
    form.vencimiento_fecha.data = ofi_documento.vencimiento_fecha
    form.contenido_sfdt.data = ofi_documento.contenido_sfdt
    # Entregar
    return render_template(
        "ofi_documentos/edit_syncfusion_document.jinja2",
        form=form,
        ofi_documento=ofi_documento,
        syncfusion_license_key=current_app.config["SYNCFUSION_LICENSE_KEY"],
    )


@ofi_documentos.route("/ofi_documentos/firmar/<int:ofi_documento_id>", methods=["GET", "POST"])
@permission_required(MODULO, Permiso.ADMINISTRAR)
def sign(ofi_documento_id):
    """Firmar un Ofi Documento"""
    ofi_documento = OfiDocumento.query.get_or_404(ofi_documento_id)
    # Validar el estatus, que no esté eliminado
    if ofi_documento.estatus != "A":
        flash("El oficio está eliminado", "warning")
        return redirect(url_for("ofi_documentos.detail", ofi_documento_id=ofi_documento.id))
    # Validar que el estado sea "BORRADOR"
    if ofi_documento.estado != "BORRADOR":
        flash("El oficio no está en estado BORRADOR, no se puede firmar", "warning")
        return redirect(url_for("ofi_documentos.detail", ofi_documento_id=ofi_documento.id))
    # Validar la fecha de vencimiento
    if ofi_documento.vencimiento_fecha is not None and ofi_documento.vencimiento_fecha < datetime.now().date():
        flash("La fecha de vencimiento no puede ser anterior a la fecha actual", "warning")
        return redirect(url_for("ofi_documentos.detail", ofi_documento_id=ofi_documento.id))
    # Formuario
    form = OfiDocumentoSignForm()
    if form.validate_on_submit():
        es_valido = True
        # Validar el folio, separar el número y el año
        folio = form.folio.data.strip()
        numero_folio = None
        anio_folio = None
        try:
            numero_folio, anio_folio = validar_folio(folio)
        except ValueError as error:
            flash(str(error), "warning")
            es_valido = False
        # Si es válido
        if es_valido:
            # Guardar en la base de datos
            ofi_documento.descripcion = safe_string(form.descripcion.data, save_enie=True)
            ofi_documento.folio = folio
            ofi_documento.folio_anio = anio_folio
            ofi_documento.folio_num = numero_folio
            ofi_documento.estado = "FIRMADO"
            ofi_documento.firma_simple_usuario_id = current_user.id
            ofi_documento.firma_simple_tiempo = datetime.now()
            ofi_documento.firma_simple = OfiDocumento.elaborar_firma(ofi_documento)
            ofi_documento.save()
            # Agregar registro a la bitácora
            bitacora = Bitacora(
                modulo=Modulo.query.filter_by(nombre=MODULO).first(),
                usuario=current_user,
                descripcion=safe_message(f"Firmado simple Ofi Documento {ofi_documento.descripcion}"),
                url=url_for("ofi_documentos.detail", ofi_documento_id=ofi_documento.id),
            )
            bitacora.save()
            flash(bitacora.descripcion, "success")
            return redirect(bitacora.url)
    # Cargar los datos en el formulario
    form.descripcion.data = ofi_documento.descripcion
    form.folio.data = ofi_documento.folio if ofi_documento.folio else "0/2025"
    form.contenido_sfdt.data = ofi_documento.contenido_sfdt
    # Entregar
    return render_template(
        "ofi_documentos/sign_syncfusion_document.jinja2",
        form=form,
        ofi_documento=ofi_documento,
        syncfusion_license_key=current_app.config["SYNCFUSION_LICENSE_KEY"],
    )


@ofi_documentos.route("/ofi_documentos/enviar/<int:ofi_documento_id>")
@permission_required(MODULO, Permiso.ADMINISTRAR)
def send(ofi_documento_id):
    """Enviar un Ofi Documento"""
    ofi_documento = OfiDocumento.query.get_or_404(ofi_documento_id)
    # Validar el estatus, que no esté eliminado
    if ofi_documento.estatus != "A":
        flash("El oficio está eliminado", "warning")
        return redirect(url_for("ofi_documentos.detail", ofi_documento_id=ofi_documento.id))
    # Validar que el estado sea "FIRMADO"
    if ofi_documento.estado != "FIRMADO":
        flash("El oficio no está en estado FIRMADO, no se puede firmar", "warning")
        return redirect(url_for("ofi_documentos.detail", ofi_documento_id=ofi_documento.id))
    # Validar que haya al menos un destinatario
    cantidad_destinatarios = (
        OfiDocumentoDestinatario.query.filter_by(ofi_documento_id=ofi_documento.id).filter_by(estatus="A").count()
    )
    if cantidad_destinatarios == 0:
        flash("Este oficio NO tiene destinatarios, no se puede enviar, debe agregarlos", "danger")
        return redirect(url_for("ofi_documentos.detail", ofi_documento_id=ofi_documento.id))
    # Actualizar el estado del documento
    ofi_documento.estado = "ENVIADO"
    ofi_documento.enviado_tiempo = datetime.now()
    ofi_documento.save()
    # TODO: Ejecutar la tarea en el fondo para enviar un mensaje a cada destinatario
    # Agregar registro a la bitácora
    bitacora = Bitacora(
        modulo=Modulo.query.filter_by(nombre=MODULO).first(),
        usuario=current_user,
        descripcion=safe_message(f"Enviado Ofi Documento {ofi_documento.descripcion}"),
        url=url_for("ofi_documentos.detail", ofi_documento_id=ofi_documento.id),
    )
    bitacora.save()
    flash(bitacora.descripcion, "success")
    return redirect(url_for("ofi_documentos.detail", ofi_documento_id=ofi_documento.id))


@ofi_documentos.route("/ofi_documentos/cancelar/<int:ofi_documento_id>")
@permission_required(MODULO, Permiso.MODIFICAR)
def cancel(ofi_documento_id):
    """Cancelar Ofi Documento"""
    ofi_documento = OfiDocumento.query.get_or_404(ofi_documento_id)
    # Validar si no está archivado
    if ofi_documento.esta_archivado:
        flash("El oficio ya está archivado", "warning")
        return redirect(url_for("ofi_documentos.detail", ofi_documento_id=ofi_documento.id))
    if ofi_documento.esta_cancelado is False:
        ofi_documento.esta_cancelado = True
        ofi_documento.save()
        bitacora = Bitacora(
            modulo=Modulo.query.filter_by(nombre=MODULO).first(),
            usuario=current_user,
            descripcion=safe_message(f"Cancelado Oficio Documento {ofi_documento.descripcion}"),
            url=url_for("ofi_documentos.detail", ofi_documento_id=ofi_documento.id),
        )
        bitacora.save()
        flash(bitacora.descripcion, "success")
    return redirect(url_for("ofi_documentos.list_active"))


@ofi_documentos.route("/ofi_documentos/descancelar/<int:ofi_documento_id>")
@permission_required(MODULO, Permiso.MODIFICAR)
def uncancel(ofi_documento_id):
    """Descancelar Ofi Documento"""
    ofi_documento = OfiDocumento.query.get_or_404(ofi_documento_id)
    # Validar si no está archivado
    if ofi_documento.esta_archivado:
        flash("El oficio ya está archivado", "warning")
        return redirect(url_for("ofi_documentos.detail", ofi_documento_id=ofi_documento.id))
    if ofi_documento.esta_cancelado is True:
        ofi_documento.esta_cancelado = False
        ofi_documento.save()
        bitacora = Bitacora(
            modulo=Modulo.query.filter_by(nombre=MODULO).first(),
            usuario=current_user,
            descripcion=safe_message(f"Descancelado Oficio Documento {ofi_documento.descripcion}"),
            url=url_for("ofi_documentos.detail", ofi_documento_id=ofi_documento.id),
        )
        bitacora.save()
        flash(bitacora.descripcion, "success")
    return redirect(url_for("ofi_documentos.detail", ofi_documento_id=ofi_documento.id))


@ofi_documentos.route("/ofi_documentos/responder/<int:ofi_documento_id>", methods=["GET", "POST"])
@permission_required(MODULO, Permiso.CREAR)
def response(ofi_documento_id):
    """Responder un Ofi Documento"""
    # Verificar que tenga una plantilla base de su autoridad
    ofi_plantilla = (
        OfiPlantilla.query.join(Usuario)
        .filter(Usuario.autoridad_id == current_user.autoridad_id)
        .filter(OfiPlantilla.estatus == "A")
        .filter(OfiPlantilla.esta_archivado == False)
        .first()
    )
    if ofi_plantilla is None:
        flash("No hay una plantilla para crear un oficio de respuesta", "warning")
        return redirect(url_for("ofi_documentos.detail", ofi_documento_id=ofi_documento_id))
    # Validar que el ofi Documento exista
    ofi_documento = OfiDocumento.query.get(ofi_documento_id)
    if ofi_documento is None:
        flash("El oficio que quiere responder no se encuentra", "warning")
        return redirect(url_for("ofi_documentos.list_active_mi_bandeja_entrada"))
    # Formulario
    form = OfiDocumentoNewForm()
    # Cargar los datos de la plantilla en el formulario
    form.descripcion.data = "RE: " + ofi_plantilla.descripcion
    form.contenido_sfdt.data = ofi_plantilla.contenido_sfdt
    form.cadena_oficio_id.data = ofi_documento_id
    # Entregar
    return render_template(
        "ofi_documentos/new_syncfusion_document.jinja2",
        form=form,
        syncfusion_license_key=current_app.config["SYNCFUSION_LICENSE_KEY"],
        ofi_plantilla_id=ofi_plantilla.id,
    )


@ofi_documentos.route("/ofi_documentos/eliminar/<int:ofi_documento_id>")
@permission_required(MODULO, Permiso.ADMINISTRAR)
def delete(ofi_documento_id):
    """Eliminar Ofi Documento"""
    ofi_documento = OfiDocumento.query.get_or_404(ofi_documento_id)
    if ofi_documento.estatus == "A":
        ofi_documento.delete()
        bitacora = Bitacora(
            modulo=Modulo.query.filter_by(nombre=MODULO).first(),
            usuario=current_user,
            descripcion=safe_message(f"Eliminado Oficio Documento {ofi_documento.descripcion}"),
            url=url_for("ofi_documentos.detail", ofi_documento_id=ofi_documento.id),
        )
        bitacora.save()
        flash(bitacora.descripcion, "success")
    return redirect(url_for("ofi_documentos.detail", ofi_documento_id=ofi_documento.id))


@ofi_documentos.route("/ofi_documentos/recuperar/<int:ofi_documento_id>")
@permission_required(MODULO, Permiso.ADMINISTRAR)
def recover(ofi_documento_id):
    """Recuperar Ofi Documento"""
    ofi_documento = OfiDocumento.query.get_or_404(ofi_documento_id)
    if ofi_documento.estatus == "B":
        ofi_documento.recover()
        bitacora = Bitacora(
            modulo=Modulo.query.filter_by(nombre=MODULO).first(),
            usuario=current_user,
            descripcion=safe_message(f"Recuperado Oficio Documento {ofi_documento.descripcion}"),
            url=url_for("ofi_documentos.detail", ofi_documento_id=ofi_documento.id),
        )
        bitacora.save()
        flash(bitacora.descripcion, "success")
    return redirect(url_for("ofi_documentos.detail", ofi_documento_id=ofi_documento.id))
