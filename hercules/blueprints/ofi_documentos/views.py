"""
Ofi Documentos, vistas
"""

import json
from datetime import datetime
from flask import Blueprint, flash, redirect, render_template, request, url_for
from flask_login import current_user, login_required
from sqlalchemy import func

from lib.datatables import get_datatable_parameters, output_datatable_json
from lib.safe_string import safe_string, safe_message

from hercules.extensions import database
from hercules.blueprints.bitacoras.models import Bitacora
from hercules.blueprints.modulos.models import Modulo
from hercules.blueprints.permisos.models import Permiso
from hercules.blueprints.usuarios.decorators import permission_required
from hercules.blueprints.ofi_documentos.models import OfiDocumento
from hercules.blueprints.ofi_documentos.forms import OfiDocumentoNewForm, OfiDocumentoEditForm, OfiDocumentoSignForm
from hercules.blueprints.ofi_plantillas.models import OfiPlantilla
from hercules.blueprints.usuarios.models import Usuario
from hercules.blueprints.ofi_documentos_destinatarios.models import OfiDocumentoDestinatario

MODULO = "OFI DOCUMENTOS"

ofi_documentos = Blueprint("ofi_documentos", __name__, template_folder="templates")


@ofi_documentos.before_request
@login_required
@permission_required(MODULO, Permiso.VER)
def before_request():
    """Permiso por defecto"""


@ofi_documentos.route("/ofi_documentos/datatable_json", methods=["GET", "POST"])
def datatable_json():
    """DataTable JSON para listado de Ofi-Documentos"""
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
    # Luego filtrar por columnas de otras tablas
    if "usuario_destinatario_id" in request.form:
        consulta = consulta.join(OfiDocumentoDestinatario)
        consulta = consulta.filter(OfiDocumentoDestinatario.usuario_id == request.form["usuario_destinatario_id"])
        consulta = consulta.filter(OfiDocumentoDestinatario.estatus == "A")
    if "usuario_autoridad_id" in request.form:
        consulta = consulta.join(Usuario)
        consulta = consulta.filter(Usuario.autoridad_id == request.form["usuario_autoridad_id"])
    # Ordenar y paginar
    registros = consulta.order_by(OfiDocumento.id.desc()).offset(start).limit(rows_per_page).all()
    total = consulta.count()
    # Elaborar datos para DataTable
    data = []
    for resultado in registros:
        data.append(
            {
                "detalle": {
                    "id": resultado.id,
                    "url": url_for("ofi_documentos.detail", ofi_documento_id=resultado.id),
                },
                "folio": resultado.folio,
                "titulo": resultado.descripcion,
                "creado": resultado.creado.strftime("%Y-%m-%d %H:%M"),
                "estado": resultado.estado,
            }
        )
    # Entregar JSON
    return output_datatable_json(draw, total, data)


@ofi_documentos.route("/ofi_documentos")
def list_active():
    """Listado de Ofi-Documentos activos"""
    return list_active_mis_oficios()


@ofi_documentos.route("/ofi_documentos/mis_oficios")
def list_active_mis_oficios():
    """Listado de Ofi-Documentos activos"""
    return render_template(
        "ofi_documentos/list.jinja2",
        filtros=json.dumps({"estatus": "A", "usuario_id": current_user.id}),
        titulo="Mis Oficios Redactados",
        estatus="A",
    )


@ofi_documentos.route("/ofi_documentos/mi_bandeja_entrada")
def list_active_mi_bandeja_entrada():
    """Listado de Ofi-Documentos donde el usuario es destinatario"""
    return render_template(
        "ofi_documentos/list.jinja2",
        filtros=json.dumps({"estatus": "A", "estado": "ENVIADO", "usuario_destinatario_id": current_user.id}),
        titulo="Oficios - Mi Bandeja de Entrada",
        estatus="A",
    )


@ofi_documentos.route("/ofi_documentos/mi_autoridad")
def list_active_mi_autoridad():
    """Listado de Ofi-Documentos de la autoridad del usuario"""
    return render_template(
        "ofi_documentos/list.jinja2",
        filtros=json.dumps({"estatus": "A", "usuario_autoridad_id": current_user.autoridad.id}),
        titulo="Oficios - Mi Autoridad",
        estatus="A",
    )


@ofi_documentos.route("/ofi_documentos/mis_oficios/inactivos")
@permission_required(MODULO, Permiso.ADMINISTRAR)
def list_inactive():
    """Listado de Ofi-Documentos inactivos"""
    return render_template(
        "ofi_documentos/list.jinja2",
        filtros=json.dumps({"estatus": "B", "usuario_id": current_user.id}),
        titulo="Mis Oficios Redactados inactivos",
        estatus="B",
    )


@ofi_documentos.route("/ofi_documentos/<int:ofi_documento_id>")
def detail(ofi_documento_id):
    """Detalle de un Ofi-Documento"""
    ofi_documento = OfiDocumento.query.get_or_404(ofi_documento_id)
    # Determinar el usuario firmante
    usuario_firmante = None
    if ofi_documento.firmante_usuario_id is not None:
        usuario_firmante = Usuario.query.get(ofi_documento.firmante_usuario_id)
    # Marcar como leído
    if ofi_documento.estado == "ENVIADO":
        # Buscar al usuario entre los destinatarios
        usuario_destinatario = (
            OfiDocumentoDestinatario.query.filter_by(ofi_documento_id=ofi_documento.id)
            .filter_by(usuario_id=current_user.id)
            .first()
        )
        if usuario_destinatario is not None and usuario_destinatario.fue_leido is False:
            usuario_destinatario.fue_leido = True
            usuario_destinatario.save()
    # Entregar
    return render_template("ofi_documentos/detail.jinja2", ofi_documento=ofi_documento, usuario_firmante=usuario_firmante)


@ofi_documentos.route("/ofi_documentos/nuevo", methods=["GET", "POST"])
@permission_required(MODULO, Permiso.CREAR)
def new():
    """Nuevo Ofi-Documento"""
    form = OfiDocumentoNewForm()
    if form.validate_on_submit():
        ofi_documento = OfiDocumento(
            usuario=current_user,
            descripcion=safe_string(form.titulo.data, save_enie=True),
            contenido=safe_message(form.contenido.data),
            estado="BORRADOR",
            es_archivado=False,
            firma_simple="",
        )
        ofi_documento.save()
        bitacora = Bitacora(
            modulo=Modulo.query.filter_by(nombre=MODULO).first(),
            usuario=current_user,
            descripcion=safe_message(f"Nuevo Oficio-Documento {ofi_documento.id}"),
            url=url_for("ofi_documentos.detail", ofi_documento_id=ofi_documento.id),
        )
        bitacora.save()
        flash(bitacora.descripcion, "success")
        return redirect(bitacora.url)
    return render_template("ofi_documentos/new.jinja2", form=form)


@ofi_documentos.route("/ofi_documentos/nuevo_con_plantilla/<int:ofi_plantilla_id>", methods=["GET", "POST"])
@permission_required(MODULO, Permiso.CREAR)
def new_with_plantilla(ofi_plantilla_id):
    """Nuevo Ofi-Documento en base a una Ofi-Plantilla"""
    ofi_plantilla = OfiPlantilla.query.get_or_404(ofi_plantilla_id)
    form = OfiDocumentoNewForm()
    # Cargar datos de la plantilla en el formulario
    form.titulo.data = ofi_plantilla.descripcion
    form.contenido.data = ofi_plantilla.contenido
    # Entregar
    return render_template("ofi_documentos/new.jinja2", form=form)


@ofi_documentos.route("/ofi_documentos/edicion/<int:ofi_documento_id>", methods=["GET", "POST"])
@permission_required(MODULO, Permiso.MODIFICAR)
def edit(ofi_documento_id):
    """Editar Oficio-Documento"""
    ofi_documento = OfiDocumento.query.get_or_404(ofi_documento_id)
    form = OfiDocumentoEditForm()
    if form.validate_on_submit():
        ofi_documento.descripcion = safe_string(form.titulo.data, save_enie=True)
        ofi_documento.folio = form.folio.data
        ofi_documento.contenido = safe_message(form.contenido.data)
        ofi_documento.save()
        bitacora = Bitacora(
            modulo=Modulo.query.filter_by(nombre=MODULO).first(),
            usuario=current_user,
            descripcion=safe_message(f"Editado Oficio-Documento {ofi_documento.descripcion}"),
            url=url_for("ofi_documentos.detail", ofi_documento_id=ofi_documento.id),
        )
        bitacora.save()
        flash(bitacora.descripcion, "success")
        return redirect(bitacora.url)
    form.titulo.data = ofi_documento.descripcion
    form.folio.data = ofi_documento.folio
    form.contenido.data = ofi_documento.contenido
    return render_template("ofi_documentos/edit.jinja2", form=form, ofi_documento=ofi_documento)


@ofi_documentos.route("/ofi_documentos/eliminar/<int:ofi_documento_id>")
@permission_required(MODULO, Permiso.ADMINISTRAR)
def delete(ofi_documento_id):
    """Eliminar Ofi-Documento"""
    ofi_documento = OfiDocumento.query.get_or_404(ofi_documento_id)
    if ofi_documento.estatus == "A":
        ofi_documento.delete()
        bitacora = Bitacora(
            modulo=Modulo.query.filter_by(nombre=MODULO).first(),
            usuario=current_user,
            descripcion=safe_message(f"Eliminado Ofi-Documento {ofi_documento.id}"),
            url=url_for("ofi_documentos.detail", ofi_documento_id=ofi_documento.id),
        )
        bitacora.save()
        flash(bitacora.descripcion, "success")
    return redirect(url_for("ofi_documentos.detail", ofi_documento_id=ofi_documento.id))


@ofi_documentos.route("/ofi_documentos/recuperar/<int:ofi_documento_id>")
@permission_required(MODULO, Permiso.ADMINISTRAR)
def recover(ofi_documento_id):
    """Recuperar Ofi-Documento"""
    ofi_documento = OfiDocumento.query.get_or_404(ofi_documento_id)
    if ofi_documento.estatus == "B":
        ofi_documento.recover()
        bitacora = Bitacora(
            modulo=Modulo.query.filter_by(nombre=MODULO).first(),
            usuario=current_user,
            descripcion=safe_message(f"Recuperado Ofi-Documento {ofi_documento.id}"),
            url=url_for("ofi_documentos.detail", ofi_documento_id=ofi_documento.id),
        )
        bitacora.save()
        flash(bitacora.descripcion, "success")
    return redirect(url_for("ofi_documentos.detail", ofi_documento_id=ofi_documento.id))


def _numero_maximo_de_folio() -> int:
    """Calcula el número máximo de folio de un Ofi-Documento"""

    # Inicializar sesión a la base de datos
    session = database.session()
    # Calcular el año actual
    fecha_actual = datetime(datetime.now().year, 12, 31, 23, 59, 59)
    # Query para calcular el número máximo de folio de una autoridad del usuario actual
    numero_max_folio = (
        session.query(func.max(OfiDocumento.folio))
        .join(Usuario)
        .filter(Usuario.autoridad_id == current_user.autoridad_id)
        .filter(OfiDocumento.creado <= fecha_actual)
        .scalar()
    )
    if numero_max_folio is None:
        numero_max_folio = 0
    return numero_max_folio


@ofi_documentos.route("/ofi_documentos/firmar/<int:ofi_documento_id>", methods=["GET", "POST"])
@permission_required(MODULO, Permiso.ADMINISTRAR)
def sign(ofi_documento_id):
    """Firmar un Ofi-Documento"""
    ofi_documento = OfiDocumento.query.get_or_404(ofi_documento_id)
    form = OfiDocumentoSignForm()
    if form.validate_on_submit():
        if ofi_documento.estado == "BORRADOR":
            es_valido = True
            # Revisar si el número de folio es válido
            folio = int(form.folio.data)
            if folio <= _numero_maximo_de_folio():
                flash("El número de folio es menor o igual a uno ya utilizado por esta autoridad", "danger")
                es_valido = False
            if es_valido:
                ofi_documento.estado = "FIRMADO"
                ofi_documento.folio = folio
                ofi_documento.firmante_usuario_id = current_user.id
                ofi_documento.save()
                # Elaborar la firma
                ofi_documento.firma_simple = OfiDocumento.elaborar_firma(ofi_documento)
                ofi_documento.save()
                # Guardar bitácora
                bitacora = Bitacora(
                    modulo=Modulo.query.filter_by(nombre=MODULO).first(),
                    usuario=current_user,
                    descripcion=safe_message(f"Ofi-Documento {ofi_documento.id} Firmado simple"),
                    url=url_for("ofi_documentos.detail", ofi_documento_id=ofi_documento.id),
                )
                bitacora.save()
                flash(bitacora.descripcion, "success")
                return redirect(bitacora.url)
    # Cargar campos
    form.titulo.data = ofi_documento.descripcion
    if ofi_documento.folio is not None:
        form.folio.data = ofi_documento.folio
    else:
        # Calcular el siguiente número de folio
        form.folio.data = _numero_maximo_de_folio() + 1
    # Entregar
    return render_template("ofi_documentos/sign.jinja2", form=form, ofi_documento=ofi_documento)


@ofi_documentos.route("/ofi_documentos/enviar/<int:ofi_documento_id>")
@permission_required(MODULO, Permiso.ADMINISTRAR)
def send(ofi_documento_id):
    """Enviar un Ofi-Documento"""
    ofi_documento = OfiDocumento.query.get_or_404(ofi_documento_id)
    # Revisar si hay almenos un destinatario
    destinatarios = OfiDocumentoDestinatario.query.filter_by(ofi_documento_id=ofi_documento.id).filter_by(estatus="A").count()
    if destinatarios is None or destinatarios <= 0:
        flash("No hay destinatarios", "danger")
        return redirect(url_for("ofi_documentos.detail", ofi_documento_id=ofi_documento.id))
    if ofi_documento.estado == "FIRMADO":
        ofi_documento.estado = "ENVIADO"
        ofi_documento.save()
        # Guardar bitácora
        bitacora = Bitacora(
            modulo=Modulo.query.filter_by(nombre=MODULO).first(),
            usuario=current_user,
            descripcion=safe_message(f"Ofi-Documento {ofi_documento.id} Enviado"),
            url=url_for("ofi_documentos.detail", ofi_documento_id=ofi_documento.id),
        )
        bitacora.save()
        flash(bitacora.descripcion, "success")
    return redirect(url_for("ofi_documentos.detail", ofi_documento_id=ofi_documento.id))
