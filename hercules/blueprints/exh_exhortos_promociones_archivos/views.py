"""
Exhortos Promociones Archivos, vistas
"""

import hashlib
import json
from datetime import datetime

from flask import Blueprint, current_app, flash, redirect, render_template, request, url_for
from flask_login import current_user, login_required
from werkzeug.datastructures import CombinedMultiDict
from werkzeug.utils import secure_filename
from werkzeug.exceptions import NotFound

from lib.datatables import get_datatable_parameters, output_datatable_json
from lib.safe_string import safe_string, safe_message

from hercules.blueprints.bitacoras.models import Bitacora
from hercules.blueprints.modulos.models import Modulo
from hercules.blueprints.permisos.models import Permiso
from hercules.blueprints.usuarios.decorators import permission_required
from hercules.blueprints.exh_exhortos_promociones_archivos.models import ExhExhortoPromocionArchivo
from hercules.blueprints.exh_exhortos_promociones.models import ExhExhortoPromocion
from lib.datatables import get_datatable_parameters, output_datatable_json
from lib.exceptions import MyBucketNotFoundError, MyFileNotFoundError, MyNotValidParamError, MyUploadError
from lib.google_cloud_storage import get_blob_name_from_url, get_file_from_gcs, upload_file_to_gcs
from hercules.blueprints.exh_exhortos_promociones_archivos.forms import (
    ExhExhortoPromocionArchivoNewForm,
    ExhExhortoPromocionArchivoEditForm,
)

MODULO = "EXH EXHORTOS PROMOCIONES ARCHIVOS"

exh_exhortos_promociones_archivos = Blueprint("exh_exhortos_promociones_archivos", __name__, template_folder="templates")


@exh_exhortos_promociones_archivos.before_request
@login_required
@permission_required(MODULO, Permiso.VER)
def before_request():
    """Permiso por defecto"""


@exh_exhortos_promociones_archivos.route("/exh_exhortos_promociones_archivos/<int:exh_exhorto_promocion_archivo_id>")
def detail(exh_exhorto_promocion_archivo_id):
    """Detalle de un Promoción Archivo"""
    exh_exhorto_promocion_archivo = ExhExhortoPromocionArchivo.query.get_or_404(exh_exhorto_promocion_archivo_id)
    return render_template(
        "exh_exhortos_promociones_archivos/detail.jinja2", exh_exhorto_promocion_archivo=exh_exhorto_promocion_archivo
    )


@exh_exhortos_promociones_archivos.route(
    "/exh_exhortos_promociones_archivos/nuevo_con_exhorto_promocion/<int:exh_exhorto_promocion_id>", methods=["GET", "POST"]
)
@permission_required(MODULO, Permiso.CREAR)
def new_with_exh_exhorto_promocion(exh_exhorto_promocion_id):
    """Nuevo Archivo con un Exhorto"""
    exh_exhorto_promocion = ExhExhortoPromocion.query.get_or_404(exh_exhorto_promocion_id)

    form = ExhExhortoPromocionArchivoNewForm(CombinedMultiDict((request.files, request.form)))
    if form.validate_on_submit():
        # Tomar el archivo del formulario
        archivo = request.files["archivo"]

        # Validar que el nombre del archivo tenga la extension PDF
        nombre_archivo = secure_filename(archivo.filename)
        if not nombre_archivo.lower().endswith(".pdf"):
            flash("El archivo debe ser un PDF", "warning")
            return redirect(url_for("exh_exhortos_promocion.detail", exh_exhorto_promocion_id=exh_exhorto_promocion_id))

        # Definir la fecha y hora de recepción
        fecha_hora_recepcion = datetime.now()

        # Insertar el registro ExhExhortoArchivo
        exh_exhorto_promocion_archivo = ExhExhortoPromocionArchivo(
            exh_exhorto_promocion=exh_exhorto_promocion,
            nombre_archivo=nombre_archivo,
            hash_sha1="",
            hash_sha256="",
            tipo_documento=form.tipo_documento.data,
            url="",
            estado="PENDIENTE",
            tamano=0,
            fecha_hora_recepcion=fecha_hora_recepcion,
        )
        exh_exhorto_promocion_archivo.save()

        # Definir el nombre del archivo a subir a Google Storage
        archivo_pdf_nombre = f"{exh_exhorto_promocion.folio_origen_promocion}-{exh_exhorto_promocion_archivo.encode_id()}.pdf"

        # Definir la ruta para blob_name con la fecha actual
        year = fecha_hora_recepcion.strftime("%Y")
        month = fecha_hora_recepcion.strftime("%m")
        day = fecha_hora_recepcion.strftime("%d")
        blob_name = f"exh_exhortos_archivos/{year}/{month}/{day}/{archivo_pdf_nombre}"

        # Subir el archivo en Google Storage
        try:
            data = archivo.stream.read()
            archivo_pdf_url = upload_file_to_gcs(
                bucket_name=current_app.config["CLOUD_STORAGE_DEPOSITO"],
                blob_name=blob_name,
                content_type="application/pdf",
                data=data,
            )
        except (MyBucketNotFoundError, MyUploadError) as error:
            exh_exhorto_promocion_archivo.delete()
            flash(str(error), "danger")
            return redirect(url_for("exh_exhortos_promociones.detail", exh_exhorto_promocion_id=exh_exhorto_promocion_id))

        # Definir con hashlib el sha1 y hash256 del archivo
        exh_exhorto_promocion_archivo.hash_sha1 = hashlib.sha1(data).hexdigest()
        exh_exhorto_promocion_archivo.hash_sha256 = hashlib.sha256(data).hexdigest()

        # Si se sube con éxito, actualizar el registro con la URL del archivo
        exh_exhorto_promocion_archivo.url = archivo_pdf_url
        exh_exhorto_promocion_archivo.tamano = len(data)
        exh_exhorto_promocion_archivo.estado = "PENDIENTE"
        exh_exhorto_promocion_archivo.save()

        # Insertar en la Bitácora
        bitacora = Bitacora(
            modulo=Modulo.query.filter_by(nombre=MODULO).first(),
            usuario=current_user,
            descripcion=safe_message(f"Nuevo Archivo {exh_exhorto_promocion_archivo.nombre_archivo}"),
            url=url_for(
                "exh_exhortos_promociones_archivos.detail", exh_exhorto_promocion_archivo_id=exh_exhorto_promocion_archivo.id
            ),
        )
        bitacora.save()

        # Mostrar mensaje de éxito y redirigir a la página del detalle del ExhExhorto
        flash(bitacora.descripcion, "success")
        return redirect(url_for("exh_exhortos_promociones.detail", exh_exhorto_promocion_id=exh_exhorto_promocion_id))

    # Entregar el formulario
    return render_template(
        "exh_exhortos_promociones_archivos/new_with_exh_exhorto_promocion.jinja2",
        form=form,
        exh_exhorto_promocion=exh_exhorto_promocion,
    )
