"""
Ofi Documentos, vistas
"""

from datetime import datetime
import json

from flask import Blueprint, current_app, flash, make_response, redirect, render_template, request, url_for
from flask_login import current_user, login_required
from werkzeug.exceptions import NotFound

from lib.datatables import get_datatable_parameters, output_datatable_json
from lib.folio import validar_folio
from lib.safe_string import safe_string, safe_message, safe_clave, safe_uuid
from hercules.blueprints.bitacoras.models import Bitacora
from hercules.blueprints.modulos.models import Modulo
from hercules.blueprints.permisos.models import Permiso
from hercules.blueprints.usuarios.decorators import permission_required
from hercules.blueprints.ofi_documentos.models import OfiDocumento
from hercules.blueprints.ofi_documentos.forms import (
    OfiDocumentoNewForm,
    OfiDocumentoEditForm,
    OfiDocumentoSignForm,
)
from hercules.blueprints.ofi_plantillas.models import OfiPlantilla
from hercules.blueprints.usuarios.models import Usuario
from hercules.blueprints.autoridades.models import Autoridad
from hercules.blueprints.ofi_documentos_destinatarios.models import OfiDocumentoDestinatario
from lib.exceptions import MyBucketNotFoundError, MyFileNotFoundError, MyNotValidParamError
from lib.google_cloud_storage import get_blob_name_from_url, get_file_from_gcs

# Roles
ROL_ESCRITOR = "OFICIOS ESCRITOR"
ROL_FIRMANTE = "OFICIOS FIRMANTE"
ROL_LECTOR = "OFICIOS LECTOR"

# Constantes para fecha de vencimiento de oficios
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
    # Determinar si se puede firmar
    puede_firmar = "OFICIOS FIRMANTE" in current_user.get_roles()
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
        usuario_id = int(request.form["usuario_id"])
        if usuario_id:
            consulta = consulta.filter(OfiDocumento.usuario_id == usuario_id)
    if "estado" in request.form:
        estado = safe_string(request.form["estado"])
        if estado:
            consulta = consulta.filter(OfiDocumento.estado == estado)
    if "folio" in request.form:
        folio = safe_string(request.form["folio"])
        if folio:
            consulta = consulta.filter(OfiDocumento.folio.contains(folio))
    if "descripcion" in request.form:
        descripcion = safe_string(request.form["descripcion"])
        if descripcion:
            consulta = consulta.filter(OfiDocumento.descripcion.contains(descripcion))
    # Filtrar por ID de autoridad
    if "autoridad_id" in request.form:
        autoridad_id = int(request.form["autoridad_id"])
        if autoridad_id:
            consulta = consulta.join(Usuario)
            consulta = consulta.filter(Usuario.autoridad_id == autoridad_id)
    # Filtrar por clave de la autoridad
    elif "autoridad_clave" in request.form:
        autoridad_clave = safe_clave(request.form["autoridad_clave"])
        if autoridad_clave:
            consulta = consulta.join(Usuario)
            consulta = consulta.join(Autoridad, Usuario.autoridad_id == Autoridad.id)
            consulta = consulta.filter(Autoridad.clave.contains(autoridad_clave))
    # Filtrar para Mi Bandeja de Entrada
    if "usuario_destinatario_id" in request.form:
        usuario_destinatario_id = int(request.form["usuario_destinatario_id"])
        if usuario_destinatario_id:
            consulta = consulta.join(OfiDocumentoDestinatario, OfiDocumentoDestinatario.ofi_documento_id == OfiDocumento.id)
            consulta = consulta.filter(OfiDocumentoDestinatario.usuario_id == request.form["usuario_destinatario_id"])
            consulta = consulta.filter(OfiDocumentoDestinatario.estatus == "A")
    # Ordenar y paginar
    registros = consulta.order_by(OfiDocumento.creado.desc()).offset(start).limit(rows_per_page).all()
    total = consulta.count()
    # Elaborar datos para DataTable
    data = []
    for resultado in registros:
        # Formar campo de vencimiento
        vencimiento_fecha = resultado.vencimiento_fecha.strftime("%Y-%m-%d") if resultado.vencimiento_fecha else "-"
        vencimiento_icono = ""
        vencimiento_titulo = ""
        dias_vencimiento = ""
        if resultado.vencimiento_fecha is not None:
            dias_vencimiento = (datetime.now().date() - resultado.vencimiento_fecha).days
            if DIAS_VENCIMIENTO_EMERGENCIA <= dias_vencimiento <= 0:
                vencimiento_icono = '<span class="iconify" data-icon="mdi:alarm-light" style="color: red;"></span>'
                vencimiento_titulo = "URGENTE"
            if DIAS_VENCIMIENTO_ADVERTENCIA <= dias_vencimiento < DIAS_VENCIMIENTO_EMERGENCIA:
                vencimiento_icono = '<span class="iconify" data-icon="mdi:alert"></span>'
                vencimiento_titulo = "FALTA POCO"
        vencimiento = f"{vencimiento_fecha} <span title='{vencimiento_titulo}'>{vencimiento_icono}</span>"
        # Icono en detalle
        icono_detalle = None
        if resultado.esta_archivado:
            icono_detalle = "ARCHIVADO"
        elif resultado.esta_cancelado:
            icono_detalle = "CANCELADO"
        # Si puede_firmar, el documento es de su autoridad y el estado es BORRADOR, se define sign_url
        sign_url = None
        if puede_firmar and resultado.usuario.autoridad_id == current_user.autoridad_id and resultado.estado == "BORRADOR":
            sign_url = url_for("ofi_documentos.sign", ofi_documento_id=resultado.id)
        # Obtener los destinatarios del oficio que tengan estatus 'A'
        destinatarios = [dest for dest in resultado.ofi_documentos_destinatarios if dest.estatus == "A"]
        # Filtrar por los destinatarios que NO han leído el oficio
        destinatarios_que_no_han_leido = [dest for dest in destinatarios if dest.fue_leido is False]
        # Si el ID del usuario esta en esta consulta, poner fila en negritas
        fila_en_negritas = current_user.id in [dest.usuario_id for dest in destinatarios_que_no_han_leido]
        # Elaborar registro
        data.append(
            {
                "detalle": {
                    "id": resultado.id,
                    "icono": icono_detalle,
                    "detail_url": url_for("ofi_documentos.detail", ofi_documento_id=resultado.id),
                    "fullscreen_url": url_for("ofi_documentos.fullscreen", ofi_documento_id=resultado.id),
                    "sign_url": sign_url,
                },
                "propietario": {
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
                    "icono": resultado.usuario.autoridad.tablero_icono if resultado.usuario.autoridad.tablero_icono else "",
                    "color_renglon": (
                        resultado.usuario.autoridad.tabla_renglon_color
                        if resultado.usuario.autoridad.tabla_renglon_color
                        else ""
                    ),
                },
                "folio": resultado.folio,
                "vencimiento": vencimiento,
                "descripcion": resultado.descripcion,
                "creado": resultado.creado.strftime("%Y-%m-%d %H:%M"),
                "estado": resultado.estado,
                "fila_en_negritas": fila_en_negritas,
            }
        )
    # Entregar JSON
    return output_datatable_json(draw, total, data)


@ofi_documentos.route("/ofi_documentos/fullscreen_json/<ofi_documento_id>", methods=["GET", "POST"])
def fullscreen_json(ofi_documento_id):
    """Entregar JSON para la vista de pantalla completa"""
    # Consultar el oficio
    ofi_documento_id = safe_uuid(ofi_documento_id)
    if not ofi_documento_id:
        return {
            "success": False,
            "message": "ID de oficio inválido.",
            "data": None,
        }
    ofi_documento = OfiDocumento.query.get_or_404(ofi_documento_id)
    # Validar que si es BORRADOR o FIRMADO se debe tener el rol ESCRITOR o FIRMANTE para verlo
    roles = current_user.get_roles()
    if (
        (ofi_documento.estado == "BORRADOR" or ofi_documento.estado == "FIRMADO")
        and ROL_ESCRITOR not in roles
        and ROL_FIRMANTE not in roles
    ):
        return {
            "success": False,
            "message": "Se necesitan roles de ESCRITOR o FIRMANTE para ver un oficio en estado BORRADOR o FIRMADO.",
            "data": None,
        }
    # Si el oficio está eliminado y NO es administrador, mostrar mensaje y redirigir
    if ofi_documento.estatus != "A" and current_user.can_admin(MODULO) is False:
        return {
            "success": False,
            "message": "Este oficio está eliminado.",
            "data": None,
        }
    # Si el estado es ENVIADO y quien lo ve es un destinatario, se va a marcar como leído
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
    # Entregar JSON
    return {
        "success": True,
        "message": "Se encontró el documento.",
        "data": {
            "pagina_cabecera_url": ofi_documento.usuario.autoridad.pagina_cabecera_url,
            "contenido_html": ofi_documento.contenido_html,
            "pagina_pie_url": ofi_documento.usuario.autoridad.pagina_pie_url,
            "firma_simple": ofi_documento.firma_simple,
            "estado": ofi_documento.estado,
        },
    }


@ofi_documentos.route("/ofi_documentos")
def list_active():
    """Listado de Ofi Documentos Mi Bandeja de Entrada"""
    return list_active_mi_bandeja_entrada()


@ofi_documentos.route("/ofi_documentos/mi_bandeja_entrada")
def list_active_mi_bandeja_entrada():
    """Listado de Ofi Documentos Mi Bandeja de Entrada"""
    # Obtener los roles del usuario
    roles = current_user.get_roles()
    # Entregar
    return render_template(
        "ofi_documentos/list.jinja2",
        filtros=json.dumps({"estatus": "A", "estado": "ENVIADO", "usuario_destinatario_id": current_user.id}),
        titulo="Mi Bandeja de Entrada",
        estatus="A",
        estados=OfiDocumento.ESTADOS,
        mostrar_boton_nuevo=ROL_FIRMANTE in roles or ROL_ESCRITOR in roles,
    )


@ofi_documentos.route("/ofi_documentos/mis_oficios")
def list_active_mis_oficios():
    """Listado de Ofi Documentos Mis Oficios"""
    # Obtener los roles del usuario
    roles = current_user.get_roles()
    # Si no se cuenta con los roles de FIRMANTE o ESCRITOR reenviarlo a vista de Bandeja de Entrada
    if ROL_FIRMANTE not in roles and ROL_ESCRITOR not in roles:
        return redirect(url_for("ofi_documentos.list_active_mi_bandeja_entrada"))
    # Entregar
    return render_template(
        "ofi_documentos/list.jinja2",
        filtros=json.dumps({"estatus": "A", "usuario_id": current_user.id}),
        titulo="Mis Oficios",
        estatus="A",
        estados=OfiDocumento.ESTADOS,
        mostrar_boton_nuevo=ROL_FIRMANTE in roles or ROL_ESCRITOR in roles,
    )


@ofi_documentos.route("/ofi_documentos/mi_autoridad")
def list_active_mi_autoridad():
    """Listado de Ofi Documentos de la autoridad del usuario"""
    # Obtener los roles del usuario
    roles = current_user.get_roles()
    # Si no se cuenta con los roles de FIRMANTE o ESCRITOR reenviarlo a vista de Bandeja de Entrada
    if ROL_FIRMANTE not in roles and ROL_ESCRITOR not in roles:
        return redirect(url_for("ofi_documentos.list_active_mi_bandeja_entrada"))
    # Entregar
    return render_template(
        "ofi_documentos/list.jinja2",
        filtros=json.dumps({"estatus": "A", "autoridad_id": current_user.autoridad.id}),
        titulo=f"Mi Autoridad {current_user.autoridad.descripcion_corta}",
        estatus="A",
        estados=OfiDocumento.ESTADOS,
        mostrar_boton_nuevo=ROL_FIRMANTE in roles or ROL_ESCRITOR in roles,
    )


@ofi_documentos.route("/ofi_documentos/eliminados")
@permission_required(MODULO, Permiso.ADMINISTRAR)
def list_inactive():
    """Listado de Ofi Documentos eliminados"""
    # Obtener los roles del usuario
    roles = current_user.get_roles()
    # Entregar
    return render_template(
        "ofi_documentos/list.jinja2",
        filtros=json.dumps({"estatus": "B"}),
        titulo="Oficios eliminados",
        estatus="B",
        estados=OfiDocumento.ESTADOS,
        mostrar_boton_nuevo=ROL_FIRMANTE in roles or ROL_ESCRITOR in roles,
    )


@ofi_documentos.route("/ofi_documentos/<ofi_documento_id>")
def detail(ofi_documento_id):
    """Detalle de un Ofi Documento"""
    # Consultar el oficio
    ofi_documento_id = safe_uuid(ofi_documento_id)
    if not ofi_documento_id:
        flash("ID de oficio inválido", "warning")
        return redirect(url_for("ofi_documentos.list_active"))
    ofi_documento = OfiDocumento.query.get_or_404(ofi_documento_id)
    # Validar que si es BORRADOR o FIRMADO se debe tener el rol ESCRITOR o FIRMANTE para verlo
    roles = current_user.get_roles()
    if (
        (ofi_documento.estado == "BORRADOR" or ofi_documento.estado == "FIRMADO")
        and ROL_ESCRITOR not in roles
        and ROL_FIRMANTE not in roles
    ):
        flash("Se necesitan roles de ESCRITOR o FIRMANTE para ver un oficio en estado BORRADOR o FIRMADO", "warning")
        return redirect(url_for("ofi_documentos.list_active"))
    # Si el oficio está eliminado y NO es administrador, mostrar mensaje y redirigir
    if ofi_documento.estatus != "A" and current_user.can_admin(MODULO) is False:
        flash("El oficio está eliminado", "warning")
        return redirect(url_for("ofi_documentos.list_active"))
    # Consultar el usuario firmante, si lo tiene
    usuario_firmante = None
    if ofi_documento.firma_simple_usuario_id is not None:
        usuario_firmante = Usuario.query.get(ofi_documento.firma_simple_usuario_id)
    # Si el usuario que lo ve es un destinatario, se va a marcar como leído
    mostrar_boton_responder = False
    platillas_opciones = None  # Si se va a responder, se van a consultar las plantillas
    if ofi_documento.estado == "ENVIADO":
        # Buscar al usuario entre los destinatarios
        usuario_destinatario = (
            OfiDocumentoDestinatario.query.filter_by(ofi_documento_id=ofi_documento.id)
            .filter_by(usuario_id=current_user.id)
            .filter_by(estatus="A")
            .first()
        )
        # Marcar como leído si es que no lo ha sido
        if usuario_destinatario is not None and usuario_destinatario.fue_leido is False:
            usuario_destinatario.fue_leido = True
            usuario_destinatario.fue_leido_tiempo = datetime.now()
            usuario_destinatario.save()
        if usuario_destinatario is not None and usuario_destinatario.con_copia is False:
            mostrar_boton_responder = True
            # Consultar las plantillas para responder
            platillas_opciones = (
                OfiPlantilla.query.join(Usuario)
                .filter(Usuario.autoridad == current_user.autoridad)
                .filter(OfiPlantilla.estatus == "A")
                .filter(OfiPlantilla.esta_archivado == False)
                .order_by(OfiPlantilla.descripcion)
                .all()
            )
    # Inicializar los valores por defecto de los boleanos de los botones
    mostrar_boton_editar = False
    mostrar_boton_firmar = False
    mostrar_boton_enviar = False
    mostrar_boton_responder = False
    mostrar_boton_archivar_desarchivar = False
    mostrar_boton_cancelar_descancelar = False
    # Definir si el usuario es de la autoridad del documento
    usuario_es_de_la_autoridad = current_user.autoridad_id == ofi_documento.usuario.autoridad_id
    # Obtener los roles
    roles = current_user.get_roles()
    # Si el usuario es FIRMANTE y es de la autoridad del documento
    if ROL_FIRMANTE in roles and usuario_es_de_la_autoridad:
        # Si el documento está en BORRADOR, se puede editar o firmar
        if ofi_documento.estado == "BORRADOR":
            mostrar_boton_editar = True
            mostrar_boton_firmar = True
        # Si el documento está en FIRMADO o enviado, se puede enviar o archivar/desarchivar
        elif ofi_documento.estado in ["FIRMADO", "ENVIADO"]:
            mostrar_boton_enviar = True
        # Si el documento NO está cancelado y NO es BORRADOR, se puede archivar/desarchivar
        if ofi_documento.esta_cancelado is False and ofi_documento.estado != "BORRADOR":
            mostrar_boton_archivar_desarchivar = True
        # Si el documento NO está en archivado, se puede cancelar o descancelar
        if ofi_documento.esta_archivado is False:
            mostrar_boton_cancelar_descancelar = True
    # Si el usuario es FIRMANTE y NO es de la autoridad del documento
    elif ROL_FIRMANTE in roles and not usuario_es_de_la_autoridad:
        # Si el documento está en ENVIADO, se puede responder
        if ofi_documento.estado == "ENVIADO":
            mostrar_boton_responder = True
    # Si el usuario es ESCRITOR y es de la autoridad del documento
    elif ROL_ESCRITOR in roles and usuario_es_de_la_autoridad:
        # Si el documento está en BORRADOR, se puede editar
        if ofi_documento.estado == "BORRADOR":
            mostrar_boton_editar = True
        # Si el documento está en FIRMADO o enviado, se puede enviar o archivar/desarchivar
        elif ofi_documento.estado in ["FIRMADO", "ENVIADO"]:
            mostrar_boton_enviar = True
        # Si el documento NO está cancelado y NO es BORRADOR, se puede archivar/desarchivar
        if ofi_documento.esta_cancelado is False and ofi_documento.estado != "BORRADOR":
            mostrar_boton_archivar_desarchivar = True
        # Si el documento NO está en archivado, se puede cancelar o descancelar
        if ofi_documento.esta_archivado is False:
            mostrar_boton_cancelar_descancelar = True
    # Si el usuario es ESCRITOR y NO es de la autoridad del documento
    elif ROL_ESCRITOR in roles and not usuario_es_de_la_autoridad:
        # Si el documento está en ENVIADO, se puede responder
        if ofi_documento.estado == "ENVIADO":
            mostrar_boton_responder = True
    # Si el usuario es ESCRITOR o FIRMANTE, mostrar botones Mis Oficios y Mi Autoridad
    mostrar_boton_mis_oficios = False
    mostrar_boton_mi_autoridad = False
    if ROL_ESCRITOR in roles or ROL_FIRMANTE in roles:
        mostrar_boton_mis_oficios = True
        mostrar_boton_mi_autoridad = True
    # Entregar el detalle
    return render_template(
        "ofi_documentos/detail.jinja2",
        ofi_documento=ofi_documento,
        usuario_firmante=usuario_firmante,
        platillas_opciones=platillas_opciones,
        mostrar_boton_mis_oficios=mostrar_boton_mis_oficios,
        mostrar_boton_mi_autoridad=mostrar_boton_mi_autoridad,
        mostrar_boton_editar=mostrar_boton_editar,
        mostrar_boton_firmar=mostrar_boton_firmar,
        mostrar_boton_enviar=mostrar_boton_enviar,
        mostrar_boton_responder=mostrar_boton_responder,
        mostrar_boton_archivar_desarchivar=mostrar_boton_archivar_desarchivar,
        mostrar_boton_cancelar_descancelar=mostrar_boton_cancelar_descancelar,
    )


@ofi_documentos.route("/ofi_documentos/pantalla_completa/<ofi_documento_id>")
def fullscreen(ofi_documento_id):
    """Pantalla completa de un Ofi Documento"""
    # Consultar el oficio
    ofi_documento_id = safe_uuid(ofi_documento_id)
    if not ofi_documento_id:
        flash("ID de oficio inválido", "warning")
        return redirect(url_for("ofi_documentos.list_active"))
    ofi_documento = OfiDocumento.query.get_or_404(ofi_documento_id)
    # Validar que si es BORRADOR o FIRMADO se debe tener el rol ESCRITOR o FIRMANTE para verlo
    roles = current_user.get_roles()
    if (
        (ofi_documento.estado == "BORRADOR" or ofi_documento.estado == "FIRMADO")
        and ROL_ESCRITOR not in roles
        and ROL_FIRMANTE not in roles
    ):
        flash("Se necesitan roles de ESCRITOR o FIRMANTE para ver un oficio en estado BORRADOR o FIRMADO", "warning")
        return redirect(url_for("ofi_documentos.list_active"))
    # Si el oficio está eliminado y NO es administrador, mostrar mensaje y redirigir
    if ofi_documento.estatus != "A" and current_user.can_admin(MODULO) is False:
        flash("El oficio está eliminado", "warning")
        return redirect(url_for("ofi_documentos.list_active"))
    # Entregar
    return render_template(
        "ofi_documentos/fullscreen.jinja2",
        ofi_documento=ofi_documento,
        mostrar_boton_mis_oficios=True,
        mostrar_boton_mi_autoridad=True,
        mostrar_boton_editar=True,
    )


@ofi_documentos.route("/ofi_documentos/pantalla_completa/documento/<ofi_documento_id>")
def fullscreen_document(ofi_documento_id):
    """Pantalla completa: contenido del frame para el documento"""
    return render_template("ofi_documentos/fullscreen_document.jinja2", ofi_documento_id=ofi_documento_id)


@ofi_documentos.route("/ofi_documentos/pantalla_completa/adjuntos/<ofi_documento_id>")
def fullscreen_attachments(ofi_documento_id):
    """Pantalla completa: contenido del frame para los adjuntos"""
    return render_template("ofi_documentos/fullscreen_attachments.jinja2", ofi_documento_id=ofi_documento_id)


@ofi_documentos.route("/ofi_documentos/pantalla_completa/destinatarios/<ofi_documento_id>")
def fullscreen_recipients(ofi_documento_id):
    """Pantalla completa: contenido del frame para los destinatarios"""
    return render_template("ofi_documentos/fullscreen_recipients.jinja2", ofi_documento_id=ofi_documento_id)


@ofi_documentos.route("/ofi_documentos/nuevo/<ofi_plantilla_id>", methods=["GET", "POST"])
@permission_required(MODULO, Permiso.CREAR)
def new(ofi_plantilla_id):
    """Nuevo Ofi Documento"""
    # Validar que el usuario tenga el rol ESCRITOR o FIRMANTE, para que un ADMINISTRADOR no pueda crear
    roles = current_user.get_roles()
    if ROL_ESCRITOR not in roles and ROL_FIRMANTE not in roles:
        flash("Se necesitan roles de ESCRITOR o FIRMANTE para crear un oficio", "warning")
        return redirect(url_for("ofi_documentos.list_active"))
    # Consultar la plantilla
    ofi_plantilla_id = safe_uuid(ofi_plantilla_id)
    if not ofi_plantilla_id:
        flash("ID de plantilla inválido", "warning")
        return redirect(url_for("ofi_plantillas.list_active"))
    ofi_plantilla = OfiPlantilla.query.get_or_404(ofi_plantilla_id)
    # Validar que la plantilla no esté eliminada
    if ofi_plantilla.estatus == "B":
        flash("La plantilla está eliminada", "warning")
        return redirect(url_for("ofi_plantillas.list_active"))
    # Validar que la plantilla no esté archivada
    if ofi_plantilla.esta_archivado:
        flash("La plantilla está archivada", "warning")
        return redirect(url_for("ofi_plantillas.list_active"))
    # Obtener el formulario
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
        # Validar que el oficio cadena exista
        ofi_documento_responder = None
        if form.cadena_oficio_id.data:
            ofi_documento_responder = OfiDocumento.query.get(form.cadena_oficio_id.data)
            if ofi_documento_responder is None:
                flash("El oficio cadena no existe", "warning")
                es_valido = False
        if es_valido:
            ofi_documento = OfiDocumento(
                usuario=current_user,
                descripcion=safe_string(form.descripcion.data, save_enie=True),
                folio=folio,
                folio_anio=anio_folio,
                folio_num=numero_folio,
                vencimiento_fecha=vencimiento_fecha,
                contenido_md=form.contenido_md.data.strip(),
                contenido_html=form.contenido_html.data.strip(),
                contenido_sfdt=form.contenido_sfdt.data.strip(),
                estado="BORRADOR",
                cadena_oficio_id=form.cadena_oficio_id.data if form.cadena_oficio_id.data else None,
            )
            ofi_documento.save()
            # Si trae una cadena de oficio, copiar el destinatario propietario
            if ofi_documento_responder:
                OfiDocumentoDestinatario(
                    ofi_documento=ofi_documento,
                    usuario=ofi_documento_responder.usuario,
                ).save()
            bitacora = Bitacora(
                modulo=Modulo.query.filter_by(nombre=MODULO).first(),
                usuario=current_user,
                descripcion=safe_message(f"Nuevo Oficio Documento {ofi_documento.descripcion}"),
                url=url_for("ofi_documentos.detail", ofi_documento_id=ofi_documento.id),
            )
            bitacora.save()
            flash(bitacora.descripcion, "success")
            return redirect(bitacora.url)
    # Sugerir el folio consultando el último documento de la autoridad del usuario
    ultimo_documento = (
        OfiDocumento.query.join(Usuario)
        .filter(Usuario.autoridad_id == current_user.autoridad_id)
        .filter(OfiDocumento.folio_anio == datetime.now().year)
        .order_by(OfiDocumento.folio_num.desc())
        .first()
    )
    if ultimo_documento:
        folio = f"{ultimo_documento.usuario.autoridad.clave}-{ultimo_documento.folio_num + 1}/{datetime.now().year}"
    else:
        folio = f"{current_user.autoridad.clave}-1/{datetime.now().year}"  # Tal vez sea el primer oficio del año
    # Reemplazar las palabras claves en el contenido HTML
    contenido_html = ofi_plantilla.contenido_html
    contenido_html = contenido_html.replace("[[DIA]]", str(datetime.now().day))
    contenido_html = contenido_html.replace("[[MES]]", str(datetime.now().strftime("%B")))
    contenido_html = contenido_html.replace("[[AÑO]]", str(datetime.now().year))
    contenido_html = contenido_html.replace("[[FOLIO]]", folio)
    # Cargar los datos de la plantilla en el formulario
    form.descripcion.data = ofi_plantilla.descripcion
    form.contenido_md.data = ofi_plantilla.contenido_md
    form.contenido_html.data = contenido_html
    form.contenido_sfdt.data = ofi_plantilla.contenido_sfdt
    form.folio.data = folio
    # Entregar el formulario
    return render_template(
        "ofi_documentos/new_ckeditor5.jinja2",
        form=form,
        ofi_plantilla_id=ofi_plantilla_id,
    )


@ofi_documentos.route("/ofi_documentos/edicion/<ofi_documento_id>", methods=["GET", "POST"])
@permission_required(MODULO, Permiso.MODIFICAR)
def edit(ofi_documento_id):
    """Editar Ofi Documento"""
    # Validar que el usuario tenga el rol ESCRITOR o FIRMANTE, para que un ADMINISTRADOR no pueda editar
    roles = current_user.get_roles()
    if ROL_ESCRITOR not in roles and ROL_FIRMANTE not in roles:
        flash("Se necesitan roles de ESCRITOR o FIRMANTE para editar un oficio", "warning")
        return redirect(url_for("ofi_documentos.list_active"))
    # Consultar el oficio
    ofi_documento_id = safe_uuid(ofi_documento_id)
    if not ofi_documento_id:
        flash("ID de oficio inválido", "warning")
        return redirect(url_for("ofi_documentos.list_active"))
    ofi_documento = OfiDocumento.query.get_or_404(ofi_documento_id)
    # Validar que la autoridad del oficio sea la misma que la del usuario
    if ofi_documento.usuario.autoridad_id != current_user.autoridad_id:
        flash("No tienes permiso para editar este oficio, pertenece a otra autoridad", "warning")
        return redirect(url_for("ofi_documentos.list_active"))
    # Validar que tenga el estado BORRADOR
    if ofi_documento.estado != "BORRADOR":
        flash("El oficio no está en estado BORRADOR, no se puede editar", "warning")
        return redirect(url_for("ofi_documentos.list_active"))
    # Validar que no esté cancelado
    if ofi_documento.esta_cancelado:
        flash("El oficio está cancelado", "warning")
        return redirect(url_for("ofi_documentos.list_active"))
    # Validar que no esté archivado
    if ofi_documento.esta_archivado:
        flash("El oficio está archivado", "warning")
        return redirect(url_for("ofi_documentos.list_active"))
    # Obtener el formulario
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
            ofi_documento.contenido_md = form.contenido_md.data.strip()
            ofi_documento.contenido_html = form.contenido_html.data.strip()
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
    form.contenido_md.data = ofi_documento.contenido_md
    form.contenido_html.data = ofi_documento.contenido_html
    form.contenido_sfdt.data = ofi_documento.contenido_sfdt
    # Si no tiene folio, sugerir el folio consultando el último documento de la autoridad del usuario
    if ofi_documento.folio is None or ofi_documento.folio == "":
        ultimo_documento = (
            OfiDocumento.query.join(Usuario)
            .filter(Usuario.autoridad_id == current_user.autoridad_id)
            .filter(OfiDocumento.folio_anio == datetime.now().year)
            .order_by(OfiDocumento.folio_num.desc())
            .first()
        )
        if ultimo_documento:
            folio = f"{ultimo_documento.usuario.autoridad.clave}-{ultimo_documento.folio_num + 1}/{datetime.now().year}"
        else:
            folio = f"{current_user.autoridad.clave}-1/{datetime.now().year}"  # Tal vez sea el primer oficio del año
        form.folio.data = folio
    # Entregar el formulario
    return render_template(
        "ofi_documentos/edit_ckeditor5.jinja2",
        form=form,
        ofi_documento=ofi_documento,
    )


@ofi_documentos.route("/ofi_documentos/renombrar/<ofi_documento_id>", methods=["GET", "POST"])
@permission_required(MODULO, Permiso.MODIFICAR)
def rename(ofi_documento_id):
    """Renombrar Ofi Documento"""
    # Consultar el oficio
    ofi_documento_id = safe_uuid(ofi_documento_id)
    if not ofi_documento_id:
        flash("ID de oficio inválido", "warning")
        return redirect(url_for("ofi_documentos.list_active"))
    ofi_documento = OfiDocumento.query.get_or_404(ofi_documento_id)
    # Validar que el usuario sea el propietario del documento
    if current_user != ofi_documento.usuario:
        flash("Solo el propietario del oficio puede renombrarlo", "warning")
        return redirect(url_for("ofi_documentos.list_active"))
    # Validar que la autoridad del oficio sea la misma que la del usuario
    if ofi_documento.usuario.autoridad_id != current_user.autoridad_id:
        flash("No tienes permiso para editar este oficio, pertenece a otra autoridad", "warning")
        return redirect(url_for("ofi_documentos.list_active"))
    # Obtener el formulario
    form = OfiDocumentoEditForm()
    if form.validate_on_submit():
        ofi_documento.descripcion = safe_string(form.descripcion.data, save_enie=True)
        ofi_documento.save()
        bitacora = Bitacora(
            modulo=Modulo.query.filter_by(nombre=MODULO).first(),
            usuario=current_user,
            descripcion=safe_message(f"Renombrado Oficio Documento descripción {ofi_documento.descripcion}"),
            url=url_for("ofi_documentos.detail", ofi_documento_id=ofi_documento.id),
        )
        bitacora.save()
        flash(bitacora.descripcion, "success")
        return redirect(bitacora.url)
    # Cargar los datos en el formulario
    form.descripcion.data = ofi_documento.descripcion
    form.vencimiento_fecha.data = ofi_documento.vencimiento_fecha
    form.folio.data = ofi_documento.folio
    # Entregar jinja2
    return render_template(
        "ofi_documentos/rename.jinja2",
        form=form,
        ofi_documento=ofi_documento,
    )


@ofi_documentos.route("/ofi_documentos/firmar/<ofi_documento_id>", methods=["GET", "POST"])
@permission_required(MODULO, Permiso.MODIFICAR)
def sign(ofi_documento_id):
    """Firmar un Ofi Documento"""
    # Validar que el usuario tenga el rol FIRMANTE
    if ROL_FIRMANTE not in current_user.get_roles():
        flash("Se necesita el rol de FIRMANTE para firmar un oficio", "warning")
        return redirect(url_for("ofi_documentos.list_active"))
    # Consultar el oficio
    ofi_documento_id = safe_uuid(ofi_documento_id)
    if not ofi_documento_id:
        flash("ID de oficio inválido", "warning")
        return redirect(url_for("ofi_documentos.list_active"))
    ofi_documento = OfiDocumento.query.get_or_404(ofi_documento_id)
    # Validar que la autoridad del oficio sea la misma que la del usuario
    if ofi_documento.usuario.autoridad_id != current_user.autoridad_id:
        flash("No tienes permiso para firmar este oficio, pertenece a otra autoridad", "warning")
        return redirect(url_for("ofi_documentos.list_active"))
    # Validar el estatus, que no esté eliminado
    if ofi_documento.estatus != "A":
        flash("El oficio está eliminado", "warning")
        return redirect(url_for("ofi_documentos.detail", ofi_documento_id=ofi_documento.id))
    # Validar que tenga el estado BORRADOR
    if ofi_documento.estado != "BORRADOR":
        flash("El oficio no está en estado BORRADOR, no se puede firmar", "warning")
        return redirect(url_for("ofi_documentos.detail", ofi_documento_id=ofi_documento.id))
    # Obtener el formuario
    form = OfiDocumentoSignForm()
    if form.validate_on_submit():
        # Validar el tipo de firma
        if form.tipo.data not in ["simple", "avanzada"]:
            flash("Tipo de firma inválido, debe ser 'simple' o 'avanzada'", "warning")
            return redirect(url_for("ofi_documentos.sign", ofi_documento_id=ofi_documento.id))
        # Actualizar
        ofi_documento.usuario = current_user  # El usuario que firma es el propietario del oficio
        ofi_documento.descripcion = safe_string(form.descripcion.data, save_enie=True)
        ofi_documento.estado = "FIRMADO"
        ofi_documento.firma_simple = OfiDocumento.elaborar_hash(ofi_documento)
        ofi_documento.firma_simple_tiempo = datetime.now()
        ofi_documento.firma_simple_usuario_id = current_user.id
        ofi_documento.save()
        # Lanzar la tarea en el fondo para convertir a archivo PDF de acuerdo al tipo de firma
        if form.tipo.data == "avanzada":
            current_user.launch_task(
                comando="ofi_documentos.tasks.lanzar_enviar_a_efirma",
                mensaje="Convirtiendo a archivo PDF con firma electrónica avanzada...",
                ofi_documento_id=str(ofi_documento.id),
            )
            descripcion = f"Oficio firmado con firma electrónica avanzada {ofi_documento.folio} {ofi_documento.descripcion}"
        elif form.tipo.data == "simple":
            current_user.launch_task(
                comando="ofi_documentos.tasks.lanzar_convertir_a_pdf",
                mensaje="Convirtiendo a archivo PDF con firma simple...",
                ofi_documento_id=str(ofi_documento.id),
            )
            descripcion = f"Oficio firmado con firma simple {ofi_documento.folio} {ofi_documento.descripcion}"
        # Agregar registro a la bitácora
        bitacora = Bitacora(
            modulo=Modulo.query.filter_by(nombre=MODULO).first(),
            usuario=current_user,
            descripcion=safe_message(descripcion),
            url=url_for("ofi_documentos.detail", ofi_documento_id=ofi_documento.id),
        )
        bitacora.save()
        flash(bitacora.descripcion, "success")
        return redirect(bitacora.url)
    # Cargar los datos en el formulario
    form.descripcion.data = ofi_documento.descripcion
    form.folio.data = ofi_documento.folio  # Read only
    form.vencimiento_fecha.data = ofi_documento.vencimiento_fecha  # Read only
    # Entregar el formulario
    return render_template(
        "ofi_documentos/sign_ckeditor5.jinja2",
        form=form,
        ofi_documento=ofi_documento,
    )


@ofi_documentos.route("/ofi_documentos/enviar/<ofi_documento_id>")
@permission_required(MODULO, Permiso.MODIFICAR)
def send(ofi_documento_id):
    """Enviar un Ofi Documento"""
    # Validar que el usuario tenga el rol ESCRITOR o FIRMANTE, para que un ADMINISTRADOR no pueda enviar
    roles = current_user.get_roles()
    if ROL_ESCRITOR not in roles and ROL_FIRMANTE not in roles:
        flash("Se necesitan roles de ESCRITOR o FIRMANTE para enviar un oficio", "warning")
        return redirect(url_for("ofi_documentos.list_active"))
    # Consultar el oficio
    ofi_documento_id = safe_uuid(ofi_documento_id)
    if not ofi_documento_id:
        flash("ID de oficio inválido", "warning")
        return redirect(url_for("ofi_documentos.list_active"))
    ofi_documento = OfiDocumento.query.get_or_404(ofi_documento_id)
    # Validar que la autoridad del oficio sea la misma que la del usuario
    if ofi_documento.usuario.autoridad_id != current_user.autoridad_id:
        flash("No tienes permiso para enviar este oficio, pertenece a otra autoridad", "warning")
        return redirect(url_for("ofi_documentos.list_active"))
    # Validar el estatus, que no esté eliminado
    if ofi_documento.estatus != "A":
        flash("El oficio está eliminado", "warning")
        return redirect(url_for("ofi_documentos.detail", ofi_documento_id=ofi_documento.id))
    # Validar que tenga el estado FIRMADO
    if ofi_documento.estado != "FIRMADO":
        flash("El oficio no está en estado FIRMADO, no se puede enviar", "warning")
        return redirect(url_for("ofi_documentos.detail", ofi_documento_id=ofi_documento.id))
    # Validar que no esté archivado
    if ofi_documento.esta_archivado:
        flash("El oficio está archivado", "warning")
        return redirect(url_for("ofi_documentos.detail", ofi_documento_id=ofi_documento.id))
    # Validar que haya al menos un destinatario
    cantidad_destinatarios = (
        OfiDocumentoDestinatario.query.filter_by(ofi_documento_id=ofi_documento.id).filter_by(estatus="A").count()
    )
    if cantidad_destinatarios == 0:
        flash("Este oficio NO tiene destinatarios, no se puede enviar, debe agregarlos", "danger")
        return redirect(url_for("ofi_documentos.detail", ofi_documento_id=ofi_documento.id))
    # Actualizar el estado a ENVIADO
    ofi_documento.estado = "ENVIADO"
    ofi_documento.enviado_tiempo = datetime.now()
    ofi_documento.save()
    # Lanzar la tarea en el fondo para enviar mensajes por correo electrónico a los destinatarios por SendGrid
    current_user.launch_task(
        comando="ofi_documentos.tasks.lanzar_enviar_a_sendgrid",
        mensaje="Enviado mensajes por correo electrónico a los destinatarios por SendGrid...",
        ofi_documento_id=str(ofi_documento.id),
    )
    # Agregar registro a la bitácora
    bitacora = Bitacora(
        modulo=Modulo.query.filter_by(nombre=MODULO).first(),
        usuario=current_user,
        descripcion=safe_message(f"Enviado Ofi Documento {ofi_documento.descripcion}"),
        url=url_for("ofi_documentos.detail", ofi_documento_id=ofi_documento.id),
    )
    bitacora.save()
    flash(bitacora.descripcion, "success")
    # Redirigir al detalle del oficio
    return redirect(url_for("ofi_documentos.detail", ofi_documento_id=ofi_documento.id))


@ofi_documentos.route("/ofi_documentos/cancelar/<ofi_documento_id>")
@permission_required(MODULO, Permiso.MODIFICAR)
def cancel(ofi_documento_id):
    """Cancelar Ofi Documento"""
    # Validar que el usuario tenga el rol ESCRITOR o FIRMANTE, para que un ADMINISTRADOR no pueda cancelar
    roles = current_user.get_roles()
    if ROL_ESCRITOR not in roles and ROL_FIRMANTE not in roles:
        flash("Se necesitan roles de ESCRITOR o FIRMANTE para cancelar un oficio", "warning")
        return redirect(url_for("ofi_documentos.list_active"))
    # Consultar el oficio
    ofi_documento_id = safe_uuid(ofi_documento_id)
    if not ofi_documento_id:
        flash("ID de oficio inválido", "warning")
        return redirect(url_for("ofi_documentos.list_active"))
    ofi_documento = OfiDocumento.query.get_or_404(ofi_documento_id)
    # Validar que la autoridad del oficio sea la misma que la del usuario
    if ofi_documento.usuario.autoridad_id != current_user.autoridad_id:
        flash("No tienes permiso para cancelar este oficio, pertenece a otra autoridad", "warning")
        return redirect(url_for("ofi_documentos.list_active"))
    # Validar que no esté archivado
    if ofi_documento.esta_archivado:
        flash("El oficio ya está archivado", "warning")
        return redirect(url_for("ofi_documentos.detail", ofi_documento_id=ofi_documento.id))
    # Validar que SI esté cancelado
    if ofi_documento.esta_cancelado is True:
        flash("El oficio ya está caneclado", "warning")
        return redirect(url_for("ofi_documentos.detail", ofi_documento_id=ofi_documento.id))
    # Actualizar esta_cancelado a verdadero
    ofi_documento.esta_cancelado = True
    ofi_documento.save()
    # Agregar registro a la bitácora
    bitacora = Bitacora(
        modulo=Modulo.query.filter_by(nombre=MODULO).first(),
        usuario=current_user,
        descripcion=safe_message(f"Cancelado Oficio Documento {ofi_documento.descripcion}"),
        url=url_for("ofi_documentos.detail", ofi_documento_id=ofi_documento.id),
    )
    bitacora.save()
    flash(bitacora.descripcion, "success")
    # Redirigir al detalle del oficio
    return redirect(url_for("ofi_documentos.detail", ofi_documento_id=ofi_documento.id))


@ofi_documentos.route("/ofi_documentos/descancelar/<ofi_documento_id>")
@permission_required(MODULO, Permiso.MODIFICAR)
def uncancel(ofi_documento_id):
    """Descancelar Ofi Documento"""
    # Validar que el usuario tenga el rol ESCRITOR o FIRMANTE, para que un ADMINISTRADOR no pueda descancelar
    roles = current_user.get_roles()
    if ROL_ESCRITOR not in roles and ROL_FIRMANTE not in roles:
        flash("Se necesitan roles de ESCRITOR o FIRMANTE para descancelar un oficio", "warning")
        return redirect(url_for("ofi_documentos.list_active"))
    # Consultar el oficio
    ofi_documento_id = safe_uuid(ofi_documento_id)
    if not ofi_documento_id:
        flash("ID de oficio inválido", "warning")
        return redirect(url_for("ofi_documentos.list_active"))
    ofi_documento = OfiDocumento.query.get_or_404(ofi_documento_id)
    # Validar que la autoridad del oficio sea la misma que la del usuario
    if ofi_documento.usuario.autoridad_id != current_user.autoridad_id:
        flash("No tienes permiso para descancelar este oficio, pertenece a otra autoridad", "warning")
        return redirect(url_for("ofi_documentos.detail", ofi_documento_id=ofi_documento.id))
    # Validar que no esté archivado
    if ofi_documento.esta_archivado:
        flash("El oficio ya está archivado", "warning")
        return redirect(url_for("ofi_documentos.detail", ofi_documento_id=ofi_documento.id))
    # Validar que NO esté cancelado
    if ofi_documento.esta_cancelado is False:
        flash("El oficio no está cancelado", "warning")
        return redirect(url_for("ofi_documentos.detail", ofi_documento_id=ofi_documento.id))
    # Actualizar esta_cancelado a falso
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
    # Redirigir al detalle del oficio
    return redirect(url_for("ofi_documentos.detail", ofi_documento_id=ofi_documento.id))


@ofi_documentos.route("/ofi_documentos/responder/<ofi_documento_id>", methods=["GET", "POST"])
@permission_required(MODULO, Permiso.CREAR)
def response(ofi_documento_id):
    """Responder un Ofi Documento"""
    # Validar que el usuario tenga el rol ESCRITOR o FIRMANTE, para que un ADMINISTRADOR no pueda responder
    roles = current_user.get_roles()
    if ROL_ESCRITOR not in roles and ROL_FIRMANTE not in roles:
        flash("Se necesitan roles de ESCRITOR o FIRMANTE para reponder un oficio", "warning")
        return redirect(url_for("ofi_documentos.list_active"))
    # Consultar el oficio
    ofi_documento_id = safe_uuid(ofi_documento_id)
    if not ofi_documento_id:
        flash("ID de oficio inválido", "warning")
        return redirect(url_for("ofi_documentos.list_active"))
    ofi_documento = OfiDocumento.query.get_or_404(ofi_documento_id)
    # Validar que no esté eliminado
    if ofi_documento.estatus != "A":
        flash("El oficio al que quiere responder está eliminado", "warning")
        return redirect(url_for("ofi_documentos.list_active"))
    # Validar que el estado sea FIRMADO o ENVIADO
    if ofi_documento.estado != "FIRMADO" and ofi_documento.estado != "ENVIADO":
        flash("El oficio al que quiere responder NO está FIRMADO o ENVIADO", "warning")
        return redirect(url_for("ofi_documentos.list_active"))
    # Validar que el usuario sea un destinatario de este oficio
    usuario_destinatario = (
        OfiDocumentoDestinatario.query.filter_by(ofi_documento_id=ofi_documento.id)
        .filter_by(usuario_id=current_user.id)
        .first()
    )
    if usuario_destinatario is None:
        flash("No eres detinatario de este oficio NO tienes permiso para responder", "warning")
        return redirect(url_for("ofi_documentos.list_active"))
    if usuario_destinatario.estatus != "A":
        flash("No eres detinatario de este oficio NO tienes permiso para responder", "warning")
        return redirect(url_for("ofi_documentos.list_active"))
    if usuario_destinatario.con_copia:
        flash("Eres destinatario con copia, NO tienes permiso para responder", "warning")
        return redirect(url_for("ofi_documentos.list_active"))
    # Si viene el UUID de la plantilla en el URL
    ofi_plantilla_id = request.args.get("plantilla_id")
    if ofi_plantilla_id is not None:
        # Validar que el UUID de la plantilla sea válido
        ofi_plantilla_id = safe_uuid(ofi_plantilla_id)
        if not ofi_plantilla_id:
            flash("ID de plantilla inválido", "warning")
            return redirect(url_for("ofi_documentos.list_active"))
    else:
        # No viene la plantilla, tomar la plantilla mas reciente de la autoridad del usuario
        ultima_plantilla = (
            OfiPlantilla.query.
            filter_by(autoridad_id=current_user.autoridad_id).
            filter_by(estatus="A").
            order_by(OfiPlantilla.creado.desc()).
            first()
        )
        if ultima_plantilla is None:
            flash("No hay plantillas disponibles en su autoridad para responder", "warning")
            return redirect(url_for("ofi_documentos.list_active"))
        ofi_plantilla_id = ultima_plantilla.id
    # Consultar la plantilla
    ofi_plantilla = OfiPlantilla.query.get(ofi_plantilla_id)
    if ofi_plantilla is None:
        flash("ID de plantilla inválido", "warning")
        return redirect(url_for("ofi_documentos.list_active"))
    # Formulario
    form = OfiDocumentoNewForm()
    # Sugerir el folio consultando el último documento de la autoridad del usuario
    ultimo_documento = (
        OfiDocumento.query.join(Usuario)
        .filter(Usuario.autoridad_id == current_user.autoridad_id)
        .filter(OfiDocumento.folio_anio == datetime.now().year)
        .order_by(OfiDocumento.folio_num.desc())
        .first()
    )
    if ultimo_documento:
        folio = f"{ultimo_documento.usuario.autoridad.clave}-{ultimo_documento.folio_num + 1}/{datetime.now().year}"
    else:
        folio = f"{current_user.autoridad.clave}-1/{datetime.now().year}"  # Tal vez sea el primer oficio del año
    # Reemplazar las palabras claves en el contenido HTML
    contenido_html = ofi_plantilla.contenido_html
    contenido_html = contenido_html.replace("[[DIA]]", str(datetime.now().day))
    contenido_html = contenido_html.replace("[[MES]]", str(datetime.now().strftime("%B")))
    contenido_html = contenido_html.replace("[[AÑO]]", str(datetime.now().year))
    contenido_html = contenido_html.replace("[[FOLIO]]", folio)
    contenido_html = contenido_html.replace("[[USUARIO]]", ofi_documento.usuario.nombre)
    contenido_html = contenido_html.replace("[[PUESTO]]", ofi_documento.usuario.puesto)
    contenido_html = contenido_html.replace("[[AUTORIDAD]]", ofi_documento.usuario.autoridad.descripcion)
    # Cargar los datos de la plantilla en el formulario
    form.descripcion.data = "RESPUESTA A " + ofi_plantilla.descripcion
    form.contenido_md.data = ofi_plantilla.contenido_md
    form.contenido_html.data = contenido_html
    form.contenido_sfdt.data = ofi_plantilla.contenido_sfdt
    form.cadena_oficio_id.data = ofi_documento_id
    form.folio.data = folio
    # Entregar el formulario
    return render_template(
        "ofi_documentos/new_ckeditor5.jinja2",
        form=form,
        ofi_plantilla_id=ofi_plantilla_id,
    )


@ofi_documentos.route("/ofi_documentos/archivar/<ofi_documento_id>")
@permission_required(MODULO, Permiso.MODIFICAR)
def archive(ofi_documento_id):
    """Archivar Ofi Documento"""
    # Validar que el usuario tenga el rol ESCRITOR o FIRMANTE, para que un ADMINISTRADOR no pueda cancelar
    roles = current_user.get_roles()
    if ROL_ESCRITOR not in roles and ROL_FIRMANTE not in roles:
        flash("Se necesitan roles de ESCRITOR o FIRMANTE para archivar un oficio", "warning")
        return redirect(url_for("ofi_documentos.list_active"))
    # Consultar el oficio
    ofi_documento_id = safe_uuid(ofi_documento_id)
    if not ofi_documento_id:
        flash("ID de oficio inválido", "warning")
        return redirect(url_for("ofi_documentos.list_active"))
    ofi_documento = OfiDocumento.query.get_or_404(ofi_documento_id)
    # Validar que la autoridad del oficio sea la misma que la del usuario
    if ofi_documento.usuario.autoridad_id != current_user.autoridad_id:
        flash("No tienes permiso para archivar este oficio, pertenece a otra autoridad", "warning")
        return redirect(url_for("ofi_documentos.list_active"))
    # Validar que no esté archivado
    if ofi_documento.esta_archivado is True:
        flash("El oficio ya está archivado", "warning")
        return redirect(url_for("ofi_documentos.detail", ofi_documento_id=ofi_documento.id))
    # Validar que SI esté cancelado
    if ofi_documento.esta_cancelado is True:
        flash("El oficio ya está caneclado", "warning")
        return redirect(url_for("ofi_documentos.detail", ofi_documento_id=ofi_documento.id))
    # Actualizar esta_archivado a verdadero
    ofi_documento.esta_archivado = True
    ofi_documento.save()
    # Agregar registro a la bitácora
    bitacora = Bitacora(
        modulo=Modulo.query.filter_by(nombre=MODULO).first(),
        usuario=current_user,
        descripcion=safe_message(f"Archivando Oficio Documento {ofi_documento.descripcion}"),
        url=url_for("ofi_documentos.detail", ofi_documento_id=ofi_documento.id),
    )
    bitacora.save()
    flash(bitacora.descripcion, "success")
    # Redirigir al detalle del oficio
    return redirect(url_for("ofi_documentos.detail", ofi_documento_id=ofi_documento.id))


@ofi_documentos.route("/ofi_documentos/desarchivar/<ofi_documento_id>")
@permission_required(MODULO, Permiso.MODIFICAR)
def unarchive(ofi_documento_id):
    """Desarchivar Ofi Documento"""
    # Validar que el usuario tenga el rol ESCRITOR o FIRMANTE, para que un ADMINISTRADOR no pueda desarchivar
    roles = current_user.get_roles()
    if ROL_ESCRITOR not in roles and ROL_FIRMANTE not in roles:
        flash("Se necesitan roles de ESCRITOR o FIRMANTE para desarchivar un oficio", "warning")
        return redirect(url_for("ofi_documentos.list_active"))
    # Consultar el oficio
    ofi_documento_id = safe_uuid(ofi_documento_id)
    if not ofi_documento_id:
        flash("ID de oficio inválido", "warning")
        return redirect(url_for("ofi_documentos.list_active"))
    ofi_documento = OfiDocumento.query.get_or_404(ofi_documento_id)
    # Validar que la autoridad del oficio sea la misma que la del usuario
    if ofi_documento.usuario.autoridad_id != current_user.autoridad_id:
        flash("No tienes permiso para desarchivar este oficio, pertenece a otra autoridad", "warning")
        return redirect(url_for("ofi_documentos.detail", ofi_documento_id=ofi_documento.id))
    # Validar que no esté archivado
    if ofi_documento.esta_archivado is False:
        flash("El oficio NO está archivado", "warning")
        return redirect(url_for("ofi_documentos.detail", ofi_documento_id=ofi_documento.id))
    # Validar que está cancelado
    if ofi_documento.esta_cancelado:
        flash("El oficio está cancelado", "warning")
        return redirect(url_for("ofi_documentos.detail", ofi_documento_id=ofi_documento.id))
    # Actualizar esta_archivado a falso
    ofi_documento.esta_archivado = False
    ofi_documento.save()
    bitacora = Bitacora(
        modulo=Modulo.query.filter_by(nombre=MODULO).first(),
        usuario=current_user,
        descripcion=safe_message(f"Desarchivar Oficio Documento {ofi_documento.descripcion}"),
        url=url_for("ofi_documentos.detail", ofi_documento_id=ofi_documento.id),
    )
    bitacora.save()
    flash(bitacora.descripcion, "success")
    # Redirigir al detalle del oficio
    return redirect(url_for("ofi_documentos.detail", ofi_documento_id=ofi_documento.id))


@ofi_documentos.route("/ofi_documentos/obtener_archivo_pdf_url_json/<ofi_documento_id>", methods=["GET", "POST"])
def get_file_pdf_url_json(ofi_documento_id):
    """Obtener el URL del archivo PDF en formato JSON, para usar en el botón de descarga"""
    # Consultar el oficio
    ofi_documento_id = safe_uuid(ofi_documento_id)
    if not ofi_documento_id:
        return {
            "success": False,
            "message": "ID de oficio inválido",
        }
    ofi_documento = OfiDocumento.query.get_or_404(ofi_documento_id)
    # Validar el estatus, que no esté eliminado
    if ofi_documento.estatus != "A":
        return {
            "success": False,
            "message": "El oficio está eliminado",
        }
    # Validar que tenga el estado FIRMADO o ENVIADO
    if ofi_documento.estado not in ["FIRMADO", "ENVIADO"]:
        return {
            "success": False,
            "message": "El oficio no está en estado FIRMADO o ENVIADO, no se puede descargar",
        }
    # Validar que tenga archivo_pdf_url
    if ofi_documento.archivo_pdf_url is None or ofi_documento.archivo_pdf_url == "":
        return {
            "success": False,
            "message": "El oficio no tiene archivo PDF, no se puede descargar. Refresque la página nuevamente.",
        }
    # Entregar el URL del archivo PDF
    return {
        "success": True,
        "message": "Archivo PDF disponible",
        "url": url_for("ofi_documentos.download_file_pdf", ofi_documento_id=ofi_documento.id),
    }


@ofi_documentos.route("/ofi_documentos/descargar_archivo_pdf/<ofi_documento_id>")
def download_file_pdf(ofi_documento_id):
    """Descargar archivo PDF"""
    # Consultar el oficio
    ofi_documento_id = safe_uuid(ofi_documento_id)
    if not ofi_documento_id:
        flash("ID de oficio inválido", "warning")
        return redirect(url_for("ofi_documentos.list_active"))
    ofi_documento = OfiDocumento.query.get_or_404(ofi_documento_id)
    # Validar el estatus, que no esté eliminado
    if ofi_documento.estatus != "A":
        flash("El oficio está eliminado", "warning")
        return redirect(url_for("ofi_documentos.detail", ofi_documento_id=ofi_documento.id))
    # Validar que tenga el estado FIRMADO o ENVIADO
    if ofi_documento.estado not in ["FIRMADO", "ENVIADO"]:
        flash("El oficio no está en estado FIRMADO o ENVIADO, no se puede descargar", "warning")
        return redirect(url_for("ofi_documentos.detail", ofi_documento_id=ofi_documento.id))
    # Validar que tenga archivo_pdf_url
    if ofi_documento.archivo_pdf_url is None or ofi_documento.archivo_pdf_url == "":
        flash("El oficio no tiene archivo PDF, no se puede descargar", "warning")
        return redirect(url_for("ofi_documentos.detail", ofi_documento_id=ofi_documento.id))
    # Obtener el contenido del archivo
    try:
        archivo = get_file_from_gcs(
            bucket_name=current_app.config["CLOUD_STORAGE_DEPOSITO_OFICIOS"],
            blob_name=get_blob_name_from_url(ofi_documento.archivo_pdf_url),
        )
    except (MyBucketNotFoundError, MyFileNotFoundError, MyNotValidParamError) as error:
        raise NotFound("No se encontró el archivo.")
    # Entregar el archivo PDF
    response = make_response(archivo)
    response.headers["Content-Type"] = "application/pdf"
    response.headers["Content-Disposition"] = f"attachment; filename={ofi_documento.folio} {ofi_documento.descripcion}.pdf"
    return response


@ofi_documentos.route("/ofi_documentos/eliminar/<ofi_documento_id>")
@permission_required(MODULO, Permiso.ADMINISTRAR)
def delete(ofi_documento_id):
    """Eliminar Ofi Documento"""
    # Consultar el oficio
    ofi_documento_id = safe_uuid(ofi_documento_id)
    if not ofi_documento_id:
        flash("ID de oficio inválido", "warning")
        return redirect(url_for("ofi_documentos.list_active"))
    ofi_documento = OfiDocumento.query.get_or_404(ofi_documento_id)
    # Validar el estatus, que no esté eliminado
    if ofi_documento.estatus != "A":
        flash("El oficio ya está eliminado", "warning")
        return redirect(url_for("ofi_documentos.detail", ofi_documento_id=ofi_documento.id))
    # Eliminar el oficio
    ofi_documento.folio = None
    ofi_documento.folio_anio = None
    ofi_documento.folio_num = None
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


@ofi_documentos.route("/ofi_documentos/recuperar/<ofi_documento_id>")
@permission_required(MODULO, Permiso.ADMINISTRAR)
def recover(ofi_documento_id):
    """Recuperar Ofi Documento"""
    # Consultar el oficio
    ofi_documento_id = safe_uuid(ofi_documento_id)
    if not ofi_documento_id:
        flash("ID de oficio inválido", "warning")
        return redirect(url_for("ofi_documentos.list_active"))
    ofi_documento = OfiDocumento.query.get_or_404(ofi_documento_id)
    # Validar el estatus, que esté eliminado
    if ofi_documento.estatus != "B":
        flash("El oficio no está eliminado", "warning")
        return redirect(url_for("ofi_documentos.detail", ofi_documento_id=ofi_documento.id))
    # Recuperar el oficio
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
