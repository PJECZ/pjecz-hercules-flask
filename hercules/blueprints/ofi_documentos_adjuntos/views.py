"""
Ofi Documentos Adjuntos, vistas
"""

import json
import os
from datetime import datetime

from flask import abort, Blueprint, flash, redirect, render_template, request, url_for, current_app, make_response
from flask_login import current_user, login_required
from werkzeug.datastructures import CombinedMultiDict
from werkzeug.exceptions import NotFound
from werkzeug.utils import secure_filename

from hercules.blueprints.bitacoras.models import Bitacora
from hercules.blueprints.modulos.models import Modulo
from hercules.blueprints.ofi_documentos_adjuntos.models import OfiDocumentoAdjunto
from hercules.blueprints.ofi_documentos_adjuntos.forms import OfiDocumentoAdjuntoForm
from hercules.blueprints.ofi_documentos.models import OfiDocumento
from hercules.blueprints.permisos.models import Permiso
from hercules.blueprints.usuarios.decorators import permission_required
from lib.datatables import get_datatable_parameters, output_datatable_json
from lib.exceptions import (
    MyBucketNotFoundError,
    MyFileNotFoundError,
    MyNotValidParamError,
    MyUploadError,
)
from lib.google_cloud_storage import get_blob_name_from_url, get_file_from_gcs, upload_file_to_gcs, EXTENSIONS_MEDIA_TYPES
from lib.safe_string import safe_string, safe_message, safe_uuid

MODULO = "OFI DOCUMENTOS ADJUNTOS"

ofi_documentos_adjuntos = Blueprint("ofi_documentos_adjuntos", __name__, template_folder="templates")

MAX_FILE_SIZE_MB = 20
MAX_FILE_SIZE_BYTES = MAX_FILE_SIZE_MB * 1024 * 1024


@ofi_documentos_adjuntos.before_request
@login_required
@permission_required(MODULO, Permiso.VER)
def before_request():
    """Permiso por defecto"""


@ofi_documentos_adjuntos.route("/ofi_documentos_adjuntos/datatable_json", methods=["GET", "POST"])
def datatable_json():
    """DataTable JSON para listado de archivos adjuntos"""
    # Tomar parámetros de Datatables
    draw, start, rows_per_page = get_datatable_parameters()
    # Consultar
    consulta = OfiDocumentoAdjunto.query
    # Primero filtrar por columnas propias
    if "estatus" in request.form:
        consulta = consulta.filter_by(estatus=request.form["estatus"])
    else:
        consulta = consulta.filter_by(estatus="A")
    if "ofi_documento_id" in request.form:
        consulta = consulta.filter_by(ofi_documento_id=request.form["ofi_documento_id"])
    # Ordenar y paginar
    registros = consulta.order_by(OfiDocumentoAdjunto.id).offset(start).limit(rows_per_page).all()
    total = consulta.count()
    # Elaborar datos para DataTable
    data = []
    for resultado in registros:
        data.append(
            {
                "detalle": {
                    "id": resultado.id,
                    "url": url_for("ofi_documentos_adjuntos.detail", ofi_documento_adjunto_id=resultado.id),
                },
                "descripcion": resultado.descripcion,
                "acciones": url_for("ofi_documentos_adjuntos.delete", ofi_documento_adjunto_id=resultado.id),
            }
        )
    # Entregar JSON
    return output_datatable_json(draw, total, data)


@ofi_documentos_adjuntos.route("/ofi_documentos_adjuntos/fullscreen_json/<ofi_documento_id>", methods=["GET", "POST"])
def fullscreen_json(ofi_documento_id):
    """Entregar JSON para la vista de pantalla completa"""
    # Validar el UUID del oficio
    ofi_documento_id = safe_uuid(ofi_documento_id)
    if not ofi_documento_id:
        return {
            "success": False,
            "message": "ID de oficio inválido.",
            "data": None,
        }
    # Consultar
    consulta = (
        OfiDocumentoAdjunto.query.filter_by(ofi_documento_id=ofi_documento_id)
        .filter_by(estatus="A")
        .order_by(OfiDocumentoAdjunto.descripcion)
        .all()
    )
    # Si no hay adjuntos, entregar mensaje fallido
    if not consulta:
        return {
            "success": False,
            "message": "Este oficio no tiene archivos adjuntos.",
            "data": None,
        }
    # Entregar JSON
    return {
        "success": True,
        "message": f"Se encontraron {len(consulta)} documentos adjuntos.",
        "data": [{"descripcion": item.descripcion, "archivo": item.archivo, "url": item.url} for item in consulta],
    }


@ofi_documentos_adjuntos.route("/ofi_documentos_adjuntos")
def list_active():
    """Listado de archivos adjuntos activos"""
    return render_template(
        "ofi_documentos_adjuntos/list.jinja2",
        filtros=json.dumps({"estatus": "A"}),
        titulo="Documentos Adjuntos",
        estatus="A",
    )


@ofi_documentos_adjuntos.route("/ofi_documentos_adjuntos/inactivos")
@permission_required(MODULO, Permiso.ADMINISTRAR)
def list_inactive():
    """Listado de archivos adjuntos inactivos"""
    return render_template(
        "ofi_documentos_adjuntos/list.jinja2",
        filtros=json.dumps({"estatus": "B"}),
        titulo="Documentos Adjuntos inactivos",
        estatus="B",
    )


@ofi_documentos_adjuntos.route("/ofi_documentos_adjuntos/<ofi_documento_adjunto_id>")
def detail(ofi_documento_adjunto_id):
    """Detalle de un archivo adjunto"""
    # Consultar el archivo adjunto
    ofi_documento_adjunto = OfiDocumentoAdjunto.query.get_or_404(ofi_documento_adjunto_id)
    # Mostrar boton de quitar
    mostrar_boton_quitar = (
        ofi_documento_adjunto.ofi_documento.estado == "BORRADOR"
        or ofi_documento_adjunto.ofi_documento.estado == "FIRMADO"
        and not ofi_documento_adjunto.ofi_documento.esta_cancelado
        and not ofi_documento_adjunto.ofi_documento.esta_archivado
    )
    # Entregar plantilla
    return render_template(
        "ofi_documentos_adjuntos/detail.jinja2",
        ofi_documento_adjunto=ofi_documento_adjunto,
        mostrar_boton_quitar=mostrar_boton_quitar,
    )


@ofi_documentos_adjuntos.route("/ofi_documentos_adjuntos/nuevo/<ofi_documento_id>", methods=["GET", "POST"])
@permission_required(MODULO, Permiso.CREAR)
def new_with_ofi_documento(ofi_documento_id):
    """Nuevo archivo adjunto"""
    ofi_documento = OfiDocumento.query.get_or_404(ofi_documento_id)

    # Recibir el formulario
    form = OfiDocumentoAdjuntoForm(CombinedMultiDict((request.files, request.form)))
    if form.validate_on_submit():
        es_valido = True

        # Hacer un listado de extensiones permitidas
        extensiones_permitidas = list(EXTENSIONS_MEDIA_TYPES.keys())

        # Tomar el archivo del formulario
        archivo = request.files["archivo"]

        # Validar la extensión del archivo
        nombre_archivo = secure_filename(archivo.filename)
        extension = nombre_archivo.rsplit(".", 1)[1].lower()
        if extension not in extensiones_permitidas:
            flash(f"Extensión no permitida. Solo se permiten: {', '.join(extensiones_permitidas)}", "warning")
            es_valido = False

        # Validar que no supere el tamaño máximo permitido de MAX_FILE_SIZE_MB
        archivo.seek(0, os.SEEK_END)
        file_size = archivo.tell()
        archivo.seek(0)
        if file_size > MAX_FILE_SIZE_BYTES:
            flash(f"El archivo es demasiado grande. Tamaño máximo permitido: {MAX_FILE_SIZE_MB} MB.", "warning")
            es_valido = False

        # Si todo es correcto, proceder
        if es_valido:
            # Definir la fecha y hora de recepción
            fecha_hora_recepcion = datetime.now()

            # Insertar el registro
            ofi_documento_adjunto = OfiDocumentoAdjunto(
                ofi_documento=ofi_documento,
                descripcion=safe_string(form.descripcion.data),
            )
            ofi_documento_adjunto.save()

            # Definir el nombre del archivo a subir a GCS
            archivo_nombre = f"{str(ofi_documento_adjunto.id)}.{extension}"

            # Definir la ruta para blob_name con la fecha actual
            year = fecha_hora_recepcion.strftime("%Y")
            month = fecha_hora_recepcion.strftime("%m")
            day = fecha_hora_recepcion.strftime("%d")
            blob_name = f"ofi_documentos_adjuntos/{year}/{month}/{day}/{archivo_nombre}"

            # Subir el archivo a GCS
            try:
                data = archivo.stream.read()
                archivo_pdf_url = upload_file_to_gcs(
                    bucket_name=current_app.config["CLOUD_STORAGE_DEPOSITO_OFICIOS"],
                    blob_name=blob_name,
                    content_type=EXTENSIONS_MEDIA_TYPES[extension],
                    data=data,
                )
            except (MyBucketNotFoundError, MyUploadError) as error:
                ofi_documento_adjunto.delete()
                flash(str(error), "danger")
                return redirect(url_for("ofi_documentos.detail", ofi_documento_id=ofi_documento_id))

            # Actualizar ofi_documento_adjunto
            ofi_documento_adjunto.archivo = nombre_archivo
            ofi_documento_adjunto.url = archivo_pdf_url
            ofi_documento_adjunto.save()

            # Insertar en la Bitácora
            bitacora = Bitacora(
                modulo=Modulo.query.filter_by(nombre=MODULO).first(),
                usuario=current_user,
                descripcion=safe_message(f"Nuevo archivo adjunto {ofi_documento_adjunto.descripcion}"),
                url=url_for("ofi_documentos.detail", ofi_documento_id=ofi_documento_id),
            )
            bitacora.save()

            # Mostrar mensaje de éxito y redirigir a la página del detalle
            flash(bitacora.descripcion, "success")

    # Limpiar el formulario
    form.descripcion.data = ""
    form.archivo.data = None

    # Entregar el formulario
    return render_template("ofi_documentos_adjuntos/new.jinja2", form=form, ofi_documento=ofi_documento)


@ofi_documentos_adjuntos.route("/ofi_documentos_adjuntos/eliminar_todos/<ofi_documento_id>")
@permission_required(MODULO, Permiso.MODIFICAR)
def remove_all(ofi_documento_id):
    """Eliminar todos los archivos adjuntos"""
    ofi_documento = OfiDocumento.query.get_or_404(ofi_documento_id)
    adjuntos = OfiDocumentoAdjunto.query.filter_by(ofi_documento_id=ofi_documento_id).filter_by(estatus="A").all()
    if not adjuntos:
        flash("No hay archivo adjuntos para eliminar", "warning")
        return redirect(url_for("ofi_documentos_adjuntos.new_with_ofi_documento", ofi_documento_id=ofi_documento_id))
    for adjunto in adjuntos:
        adjunto.delete()
    bitacora = Bitacora(
        modulo=Modulo.query.filter_by(nombre=MODULO).first(),
        usuario=current_user,
        descripcion=safe_message(f"Eliminados todos los archivos adjuntos del oficio {ofi_documento.descripcion}"),
        url=url_for("ofi_documentos.detail", ofi_documento_id=ofi_documento.id),
    )
    bitacora.save()
    flash(bitacora.descripcion, "success")
    return redirect(url_for("ofi_documentos_adjuntos.new_with_ofi_documento", ofi_documento_id=ofi_documento_id))


@ofi_documentos_adjuntos.route("/ofi_documentos_adjuntos/eliminar/<ofi_documento_adjunto_id>")
@permission_required(MODULO, Permiso.MODIFICAR)
def delete(ofi_documento_adjunto_id):
    """Eliminar un archivo adjunto"""
    ofi_documento_adjunto = OfiDocumentoAdjunto.query.get_or_404(ofi_documento_adjunto_id)
    if ofi_documento_adjunto.estatus == "A":
        ofi_documento_adjunto.delete()
        bitacora = Bitacora(
            modulo=Modulo.query.filter_by(nombre=MODULO).first(),
            usuario=current_user,
            descripcion=safe_message(f"Eliminado archivo adjunto {ofi_documento_adjunto.descripcion}"),
            url=url_for("ofi_documentos_adjuntos.detail", ofi_documento_adjunto_id=ofi_documento_adjunto.id),
        )
        bitacora.save()
        flash(bitacora.descripcion, "success")
    return redirect(
        url_for("ofi_documentos_adjuntos.new_with_ofi_documento", ofi_documento_id=ofi_documento_adjunto.ofi_documento_id)
    )


@ofi_documentos_adjuntos.route("/ofi_documentos_adjuntos/recuperar/<ofi_documento_adjunto_id>")
@permission_required(MODULO, Permiso.ADMINISTRAR)
def recover(ofi_documento_adjunto_id):
    """Recuperar un archivo adjunto"""
    ofi_documento_adjunto = OfiDocumentoAdjunto.query.get_or_404(ofi_documento_adjunto_id)
    if ofi_documento_adjunto.estatus == "B":
        ofi_documento_adjunto.recover()
        bitacora = Bitacora(
            modulo=Modulo.query.filter_by(nombre=MODULO).first(),
            usuario=current_user,
            descripcion=safe_message(f"Recuperado archivo adjunto {ofi_documento_adjunto.descripcion}"),
            url=url_for("ofi_documentos_adjuntos.detail", ofi_documento_adjunto_id=ofi_documento_adjunto.id),
        )
        bitacora.save()
        flash(bitacora.descripcion, "success")
    return redirect(url_for("ofi_documentos.detail", ofi_documento_id=ofi_documento_adjunto.ofi_documento_id))


@ofi_documentos_adjuntos.route("/ofi_documentos_adjuntos/<ofi_documento_adjunto_id>/doc_xls")
def download_doc_xls(ofi_documento_adjunto_id):
    """Descargar el archivo adjunto de tipo DOC o XLS"""

    # Consultar
    adjunto = OfiDocumentoAdjunto.query.get_or_404(ofi_documento_adjunto_id)

    # Si está eliminado, es decir con estatus "B", no se puede descargar, provocar un error 404
    if adjunto.estatus == "B":
        abort(404)

    # Tomar la extension a partir del nombre del archivo
    extension = adjunto.archivo.rsplit(".", 1)[1].lower()

    # Definir el nombre del archivo para la descarga juntando el folio del oficio y la descripción del archivo
    archivo_nombre = f"{adjunto.ofi_documento.folio}-{safe_string(adjunto.descripcion)}.{extension}"
    archivo_nombre = secure_filename(archivo_nombre)

    # Obtener el contenido del archivo desde GCS
    try:
        descarga_contenido = get_file_from_gcs(
            bucket_name=current_app.config["CLOUD_STORAGE_DEPOSITO_OFICIOS"],
            blob_name=get_blob_name_from_url(adjunto.url),
        )
    except (MyBucketNotFoundError, MyFileNotFoundError, MyNotValidParamError) as error:
        flash(str(error), "danger")
        return redirect(url_for("ofi_documentos_adjuntos.detail", ofi_documento_adjunto_id=adjunto.id))

    # Descargar un archivo DOC o XLS
    response = make_response(descarga_contenido)
    response.headers["Content-Type"] = "application/doc"
    response.headers["Content-Disposition"] = f"attachment; filename={archivo_nombre}"
    return response


@ofi_documentos_adjuntos.route("/ofi_documentos_adjuntos/<ofi_documento_adjunto_id>/pdf")
def download_pdf(ofi_documento_adjunto_id):
    """Descargar el archivo PDF de un archivo adjunto"""

    # Consultar el archivo adjunto, si no existe, error 404
    adjunto = OfiDocumentoAdjunto.query.get_or_404(ofi_documento_adjunto_id)

    # Si está eliminado, es decir con estatus "B", no se puede descargar, provocar un error 404
    if adjunto.estatus == "B":
        abort(404)

    # Definir el nombre del archivo para la descarga juntando el folio del oficio y la descripción del archivo
    archivo_nombre = f"{adjunto.ofi_documento.folio}-{safe_string(adjunto.descripcion)}.pdf"
    archivo_nombre = secure_filename(archivo_nombre)

    # Obtener el contenido del archivo desde GCS
    try:
        descarga_contenido = get_file_from_gcs(
            bucket_name=current_app.config["CLOUD_STORAGE_DEPOSITO_OFICIOS"],
            blob_name=get_blob_name_from_url(adjunto.url),
        )
    except (MyBucketNotFoundError, MyFileNotFoundError, MyNotValidParamError) as error:
        flash(str(error), "danger")
        return redirect(url_for("ofi_documentos_adjuntos.detail", ofi_documento_adjunto_id=adjunto.id))

    # Descargar el archivo adjunto en PDF
    response = make_response(descarga_contenido)
    response.headers["Content-Type"] = "application/pdf"
    response.headers["Content-Disposition"] = f"attachment; filename={archivo_nombre}"
    return response


@ofi_documentos_adjuntos.route("/ofi_documentos_adjuntos/ver_archivo_pdf/<ofi_documento_adjunto_id>")
def view_file_pdf(ofi_documento_adjunto_id):
    """Ver archivo PDF de un archivo adjunto para insertarlo en un iframe"""

    # Consultar el archivo adjunto, si no existe, error 404
    adjunto = OfiDocumentoAdjunto.query.get_or_404(ofi_documento_adjunto_id)

    # Si está eliminado, es decir con estatus "B", no se puede descargar, provocar un error 404
    if adjunto.estatus == "B":
        abort(404)

    # Obtener el contenido del archivo
    try:
        archivo = get_file_from_gcs(
            bucket_name=current_app.config["CLOUD_STORAGE_DEPOSITO_OFICIOS"],
            blob_name=get_blob_name_from_url(adjunto.url),
        )
    except (MyBucketNotFoundError, MyFileNotFoundError, MyNotValidParamError):
        abort(500)

    # Entregar el archivo
    response = make_response(archivo)
    response.headers["Content-Type"] = "application/pdf"
    return response


@ofi_documentos_adjuntos.route("/ofi_documentos_adjuntos/ver_archivo_img/<ofi_documento_adjunto_id>")
def view_file_img(ofi_documento_adjunto_id):
    """Ver archivo IMG de un archivo adjunto para insertarlo en un iframe"""

    # Consultar
    adjunto = OfiDocumentoAdjunto.query.get_or_404(ofi_documento_adjunto_id)

    # Si está eliminado, es decir con estatus "B", no se puede descargar, provocar un error 404
    if adjunto.estatus == "B":
        abort(404)

    # Obtener el contenido del archivo
    try:
        archivo = get_file_from_gcs(
            bucket_name=current_app.config["CLOUD_STORAGE_DEPOSITO_OFICIOS"],
            blob_name=get_blob_name_from_url(adjunto.url),
        )
    except (MyBucketNotFoundError, MyFileNotFoundError, MyNotValidParamError):
        abort(500)

    # Entregar el archivo
    response = make_response(archivo)
    response.headers["Content-Type"] = "image/jpeg"
    return response
