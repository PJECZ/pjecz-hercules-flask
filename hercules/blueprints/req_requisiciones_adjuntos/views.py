"""
Req Requisiones Adjuntos, vistas
"""

import json
import os
from flask import Blueprint, current_app, flash, redirect, render_template, request, url_for, make_response
from flask_login import current_user, login_required
from werkzeug.datastructures import CombinedMultiDict

from lib.datatables import get_datatable_parameters, output_datatable_json
from lib.safe_string import safe_string, safe_message
from werkzeug.exceptions import NotFound

from lib.datatables import get_datatable_parameters, output_datatable_json
from lib.exceptions import MyBucketNotFoundError, MyFileNotFoundError, MyNotValidParamError, MyUploadError
from lib.exceptions import (
    MyFilenameError,
    MyMissingConfigurationError,
    MyNotAllowedExtensionError,
    MyUnknownExtensionError,
)
from lib.google_cloud_storage import get_blob_name_from_url, get_file_from_gcs, upload_file_to_gcs
from lib.storage import GoogleCloudStorage
from hercules.blueprints.bitacoras.models import Bitacora
from hercules.blueprints.modulos.models import Modulo
from hercules.blueprints.permisos.models import Permiso
from hercules.blueprints.usuarios.decorators import permission_required
from hercules.blueprints.req_requisiciones_adjuntos.models import ReqRequisicionAdjunto
from hercules.blueprints.req_requisiciones_adjuntos.forms import ReqRequisicionAdjuntoForm
from hercules.blueprints.req_requisiciones.models import ReqRequisicion


MODULO = "REQ REQUISICIONES ADJUNTOS"

req_requisiciones_adjuntos = Blueprint("req_requisiciones_adjuntos", __name__, template_folder="templates")

SUBDIRECTORIO = "requisiciones_adjuntos"
MAX_FILE_SIZE_MB = 20
MAX_FILE_SIZE_BYTES = MAX_FILE_SIZE_MB * 1024 * 1024


@req_requisiciones_adjuntos.before_request
@login_required
@permission_required(MODULO, Permiso.VER)
def before_request():
    """Permiso por defecto"""


@req_requisiciones_adjuntos.route("/req_requisiciones_adjuntos/datatable_json", methods=["GET", "POST"])
def datatable_json():
    """DataTable JSON para listado de Req Requisiciones Adjuntos"""
    # Tomar parámetros de Datatables
    draw, start, rows_per_page = get_datatable_parameters()
    # Consultar
    consulta = ReqRequisicionAdjunto.query
    # Primero filtrar por columnas propias
    if "estatus" in request.form:
        consulta = consulta.filter_by(estatus=request.form["estatus"])
    else:
        consulta = consulta.filter_by(estatus="A")
    if "req_requisicion_id" in request.form:
        consulta = consulta.filter_by(req_requisicion_id=request.form["req_requisicion_id"])
    # Ordenar y paginar
    registros = consulta.order_by(ReqRequisicionAdjunto.id).offset(start).limit(rows_per_page).all()
    total = consulta.count()
    # Elaborar datos para DataTable
    data = []
    for resultado in registros:
        data.append(
            {
                "detalle": {
                    "id": resultado.id,
                    "url": url_for("req_requisiciones_adjuntos.detail", req_requisicion_adjunto_id=resultado.id),
                },
                "descripcion": resultado.descripcion,
                "acciones": url_for("req_requisiciones_adjuntos.delete", req_requisicion_adjunto_id=resultado.id),
            }
        )
    # Entregar JSON
    return output_datatable_json(draw, total, data)


@req_requisiciones_adjuntos.route("/req_requisiciones_adjuntos")
def list_active():
    """Listado de Req Requisiciones Adjuntos activos"""
    return render_template(
        "req_requisiciones_adjuntos/list.jinja2",
        filtros=json.dumps({"estatus": "A"}),
        titulo="Documentos Adjuntos",
        estatus="A",
    )


@req_requisiciones_adjuntos.route("/req_requisiciones_adjuntos/inactivos")
@permission_required(MODULO, Permiso.ADMINISTRAR)
def list_inactive():
    """Listado de Req Requisiciones Adjuntos inactivos"""
    return render_template(
        "req_requisiciones_adjuntos/list.jinja2",
        filtros=json.dumps({"estatus": "B"}),
        titulo="Documentos Adjuntos inactivos",
        estatus="B",
    )


@req_requisiciones_adjuntos.route("/req_requisiciones_adjuntos/<req_requisicion_adjunto_id>")
def detail(req_requisicion_adjunto_id):
    """Detalle de un Req Requisiciones Adjunto"""
    req_requisicion_adjunto = ReqRequisicionAdjunto.query.get_or_404(req_requisicion_adjunto_id)
    req_requisicion = ReqRequisicion.query.get_or_404(req_requisicion_adjunto.req_requisicion_id)
    # Mostrar botón de quitar
    mostrar_boton_quitar = False
    if (
        req_requisicion.estado == "BORRADOR"
        or req_requisicion.estado == "FIRMADO"
        and not req_requisicion.esta_cancelado
        and not req_requisicion.esta_archivado
    ):
        mostrar_boton_quitar = True
    # Entregar plantilla
    return render_template(
        "req_requisiciones_adjuntos/detail.jinja2",
        req_requisicion_adjunto=req_requisicion_adjunto,
        mostrar_boton_quitar=mostrar_boton_quitar,
    )


@req_requisiciones_adjuntos.route("/req_requisiciones_adjuntos/nuevo/<req_requisicion_id>", methods=["GET", "POST"])
@permission_required(MODULO, Permiso.CREAR)
def new_with_ofi_documento(req_requisicion_id):
    """Nuevo Requisición-Documento-Adjunto"""
    req_requisicion = ReqRequisicion.query.get_or_404(req_requisicion_id)
    form = ReqRequisicionAdjuntoForm(CombinedMultiDict((request.files, request.form)))
    if form.validate_on_submit():
        es_valido = True
        # Guardar cambios con un archivo adjunto
        # Validar archivo
        archivo = request.files["archivo"]
        # Validar que no supere el tamaño máximo permitido de MAX_FILE_SIZE_MB
        if archivo:
            archivo.seek(0, os.SEEK_END)
            file_size = archivo.tell()
            archivo.seek(0)
            if file_size > MAX_FILE_SIZE_BYTES:
                flash(f"El archivo es demasiado grande. Tamaño máximo permitido: {MAX_FILE_SIZE_MB} MB.", "warning")
                es_valido = False
        storage = GoogleCloudStorage(
            base_directory=SUBDIRECTORIO, allowed_extensions=["pdf", "jpg", "jpeg", "png", "doc", "docx", "xls", "xlsx"]
        )
        try:
            storage.set_content_type(archivo.filename)
        except MyNotAllowedExtensionError:
            flash("Tipo de archivo no permitido.", "warning")
            es_valido = False
        except MyUnknownExtensionError:
            flash("Tipo de archivo desconocido.", "warning")
            es_valido = False
        if es_valido:
            # crear un nuevo registro
            req_requisicion_adjunto = ReqRequisicionAdjunto(
                req_requisicion=req_requisicion,
                descripcion=safe_string(form.descripcion.data),
            )
            req_requisicion_adjunto.save()
            # Subir a Google Cloud Storage
            es_exitoso = True
            try:
                storage.set_filename(
                    hashed_id=req_requisicion_adjunto.encode_id(), description=req_requisicion_adjunto.descripcion
                )
                # storage.set_content_type(archivo.tipo)
                storage.upload(archivo.stream.read())
            except (MyFilenameError, MyNotAllowedExtensionError, MyUnknownExtensionError):
                flash("Error fatal al subir el archivo a GCS.", "warning")
                es_exitoso = False
            except MyMissingConfigurationError:
                flash("Error al subir el archivo porque falla la configuración de GCS.", "danger")
                es_exitoso = False
            except Exception:
                flash("Error desconocido al subir el archivo.", "danger")
                es_exitoso = False
            # Remplazar archivo
            if es_exitoso:
                req_requisicion_adjunto.archivo = storage.filename
                req_requisicion_adjunto.url = storage.url
                req_requisicion_adjunto.save()
                # Salida en bitácora
                bitacora = Bitacora(
                    modulo=Modulo.query.filter_by(nombre=MODULO).first(),
                    usuario=current_user,
                    descripcion=safe_message(f"Nueva Requisición - Documento Adjunto {req_requisicion_adjunto.descripcion}"),
                    url=url_for("req_requisiciones_adjuntos.detail", req_requisicion_adjunto_id=req_requisicion_adjunto.id),
                )
                bitacora.save()
                flash(bitacora.descripcion, "success")
                # Limpiado de campos
                form.descripcion.data = ""
                form.archivo.data = None
    # Entregar
    return render_template("req_requisiciones_adjuntos/new.jinja2", form=form, req_requisicion=req_requisicion)


@req_requisiciones_adjuntos.route("/req_requisiciones_adjuntos/eliminar_todos/<req_requisicion_id>")
@permission_required(MODULO, Permiso.MODIFICAR)
def remove_all(req_requisicion_id):
    """Eliminar Todos los Req Requisicion Adjuntos"""
    req_requisicion = ReqRequisicion.query.get_or_404(req_requisicion_id)
    adjuntos = ReqRequisicionAdjunto.query.filter_by(req_requisicion_id=req_requisicion_id).filter_by(estatus="A").all()
    if not adjuntos:
        flash("No hay archivo adjuntos para eliminar", "warning")
        return redirect(url_for("req_requisiciones_adjuntos.new_with_req_requisicion", req_requisicion_id=req_requisicion_id))
    for adjunto in adjuntos:
        adjunto.delete()

    bitacora = Bitacora(
        modulo=Modulo.query.filter_by(nombre=MODULO).first(),
        usuario=current_user,
        descripcion=safe_message(f"Eliminado todos los archivos adjuntos de la Requisición {req_requisicion.descripcion}"),
        url=url_for("req_requisiciones.detail", req_requisicion_id=req_requisicion.id),
    )
    bitacora.save()
    flash(bitacora.descripcion, "success")
    return redirect(url_for("req_requisiciones_adjuntos.new_with_req_requisicion", req_requisicion_id=req_requisicion_id))


@req_requisiciones_adjuntos.route("/req_requisiciones_adjuntos/eliminar/<req_requisicion_adjunto_id>")
@permission_required(MODULO, Permiso.MODIFICAR)
def delete(req_requisicion_adjunto_id):
    """Eliminar Requisición documento adjunto"""
    req_requisicion_adjunto = ReqRequisicionAdjunto.query.get_or_404(req_requisicion_adjunto_id)
    if req_requisicion_adjunto.estatus == "A":
        req_requisicion_adjunto.delete()
        bitacora = Bitacora(
            modulo=Modulo.query.filter_by(nombre=MODULO).first(),
            usuario=current_user,
            descripcion=safe_message(f"Eliminado Requisición documento adjunto {req_requisicion_adjunto.descripcion}"),
            url=url_for("req_requisiciones_adjuntos.detail", req_requisicion_adjunto_id=req_requisicion_adjunto.id),
        )
        bitacora.save()
        flash(bitacora.descripcion, "success")
    return redirect(
        url_for(
            "req_requisiciones_adjuntos.new_with_req_requisicion", req_requisicion_id=req_requisicion_adjunto.req_requisicion_id
        )
    )


@req_requisiciones_adjuntos.route("/req_requisiciones_adjuntos/recuperar/<req_requisicion_adjunto_id>")
@permission_required(MODULO, Permiso.ADMINISTRAR)
def recover(req_requisicion_adjunto_id):
    """Recuperar Requisición documento adjunto"""
    req_requisicion_adjunto = ReqRequisicionAdjunto.query.get_or_404(req_requisicion_adjunto_id)
    if req_requisicion_adjunto.estatus == "B":
        req_requisicion_adjunto.recover()
        bitacora = Bitacora(
            modulo=Modulo.query.filter_by(nombre=MODULO).first(),
            usuario=current_user,
            descripcion=safe_message(f"Recuperado Requisición documento adjunto {req_requisicion_adjunto.descripcion}"),
            url=url_for("req_requisiciones_adjuntos.detail", req_requisicion_adjunto_id=req_requisicion_adjunto.id),
        )
        bitacora.save()
        flash(bitacora.descripcion, "success")
    return redirect(url_for("req_requisiciones.detail", req_requisicion_id=req_requisicion_adjunto.req_requisicion_id))


@req_requisiciones_adjuntos.route("/req_requisiciones_adjuntos/<req_requisicion_adjunto_id>/pdf")
def download_pdf(req_requisicion_adjunto_id):
    """Descargar el archivo PDF de un Archivo"""

    # Consultar
    adjunto = ReqRequisicionAdjunto.query.get_or_404(req_requisicion_adjunto_id)

    # Si el estatus es B, no se puede descargar
    if adjunto.estatus == "B":
        flash("No se puede descargar un archivo inactivo", "warning")
        return redirect(url_for("req_requisiciones_adjuntos.detail", req_requisicion_adjunto_id=adjunto.id))

    # Tomar el nombre del archivo con el que sera descargado
    descarga_nombre = adjunto.archivo

    # Obtener el contenido del archivo desde Google Storage
    try:
        descarga_contenido = get_file_from_gcs(
            bucket_name=current_app.config["CLOUD_STORAGE_DEPOSITO"],
            blob_name=get_blob_name_from_url(adjunto.url),
        )
    except (MyBucketNotFoundError, MyFileNotFoundError, MyNotValidParamError) as error:
        flash(str(error), "danger")
        return redirect(url_for("req_requisiciones_adjuntos.detail", req_requisicion_adjunto_id=adjunto.id))

    # Descargar un archivo PDF
    response = make_response(descarga_contenido)
    response.headers["Content-Type"] = "application/pdf"
    response.headers["Content-Disposition"] = f"attachment; filename={descarga_nombre}"
    return response


@req_requisiciones_adjuntos.route("/req_requisiciones_adjuntos/ver_archivo_pdf/<req_requisicion_adjunto_id>")
def view_file_pdf(req_requisicion_adjunto_id):
    """Ver archivo PDF de adjunto para insertarlo en un iframe en el detalle"""

    # Consultar
    adjunto = ReqRequisicionAdjunto.query.get_or_404(req_requisicion_adjunto_id)

    # Obtener el contenido del archivo
    try:
        archivo = get_file_from_gcs(
            bucket_name=current_app.config["CLOUD_STORAGE_DEPOSITO"],
            blob_name=get_blob_name_from_url(adjunto.url),
        )
    except (MyBucketNotFoundError, MyFileNotFoundError, MyNotValidParamError) as error:
        print(adjunto.url)
        raise NotFound("No se encontró el archivo.")

    # Entregar el archivo
    response = make_response(archivo)
    response.headers["Content-Type"] = "application/pdf"
    return response


@req_requisiciones_adjuntos.route("/req_requisiciones_adjuntos/ver_archivo_img/<req_requisicion_adjunto_id>")
def view_file_img(req_requisicion_adjunto_id):
    """Ver archivo PDF de adjunto para insertarlo en un iframe en el detalle"""

    # Consultar
    adjunto = ReqRequisicionAdjunto.query.get_or_404(req_requisicion_adjunto_id)

    # Obtener el contenido del archivo
    try:
        archivo = get_file_from_gcs(
            bucket_name=current_app.config["CLOUD_STORAGE_DEPOSITO"],
            blob_name=get_blob_name_from_url(adjunto.url),
        )
    except (MyBucketNotFoundError, MyFileNotFoundError, MyNotValidParamError) as error:
        print(adjunto.url)
        raise NotFound("No se encontró el archivo.")

    # Entregar el archivo
    response = make_response(archivo)
    response.headers["Content-Type"] = "image/jpeg"
    return response


@req_requisiciones_adjuntos.route("/req_requisiciones_adjuntos/<req_requisicion_adjunto_id>/doc_xls")
def download_docs(req_requisicion_adjunto_id):
    """Descargar el archivo DOC o XLS de un Archivo"""

    # Consultar
    adjunto = ReqRequisicionAdjunto.query.get_or_404(req_requisicion_adjunto_id)

    # Si el estatus es B, no se puede descargar
    if adjunto.estatus == "B":
        flash("No se puede descargar un archivo inactivo", "warning")
        return redirect(url_for("personas_adjuntos.detail", req_requisicion_adjunto_id=adjunto.id))

    # Tomar el nombre del archivo con el que sera descargado
    descarga_nombre = adjunto.archivo

    # Obtener el contenido del archivo desde Google Storage
    try:
        descarga_contenido = get_file_from_gcs(
            bucket_name=current_app.config["CLOUD_STORAGE_DEPOSITO"],
            blob_name=get_blob_name_from_url(adjunto.url),
        )
    except (MyBucketNotFoundError, MyFileNotFoundError, MyNotValidParamError) as error:
        flash(str(error), "danger")
        return redirect(url_for("req_requisiciones_adjuntos.detail", req_requisicion_adjunto_id=adjunto.id))

    # Descargar un archivo DOC o XLS
    response = make_response(descarga_contenido)
    response.headers["Content-Type"] = "application/doc"
    response.headers["Content-Disposition"] = f"attachment; filename={descarga_nombre}"
    return response
