"""
Usuarios Nóminas, vistas
"""

import json

from flask import Blueprint, current_app, flash, make_response, redirect, render_template, request, url_for
from flask_login import current_user, login_required
from werkzeug.exceptions import NotFound

from hercules.blueprints.bitacoras.models import Bitacora
from hercules.blueprints.modulos.models import Modulo
from hercules.blueprints.permisos.models import Permiso
from hercules.blueprints.usuarios.decorators import permission_required
from hercules.blueprints.usuarios.models import Usuario
from hercules.blueprints.usuarios_nominas.models import UsuarioNomina
from lib.datatables import get_datatable_parameters, output_datatable_json
from lib.exceptions import MyBucketNotFoundError, MyFileNotFoundError, MyNotValidParamError
from lib.google_cloud_storage import get_blob_name_from_url, get_file_from_gcs
from lib.safe_string import safe_curp, safe_email, safe_message

MODULO = "USUARIOS NOMINAS"

usuarios_nominas = Blueprint("usuarios_nominas", __name__, template_folder="templates")


@usuarios_nominas.before_request
@login_required
@permission_required(MODULO, Permiso.VER)
def before_request():
    """Permiso por defecto"""


@usuarios_nominas.route("/usuarios_nominas/datatable_json", methods=["GET", "POST"])
def datatable_json():
    """DataTable JSON para listado de UsuarioNomina"""
    # Tomar parámetros de Datatables
    draw, start, rows_per_page = get_datatable_parameters()
    # Consultar
    consulta = UsuarioNomina.query
    # Primero filtrar por columnas propias
    if "usuario_id" in request.form:
        consulta = consulta.filter(UsuarioNomina.usuario_id == current_user.id)
    # Luego filtrar por columnas de otras tablas
    if "usuario_email" in request.form:
        consulta = consulta.join(Usuario)
        consulta = consulta.filter(Usuario.email.contains(safe_email(request.form["usuario_email"], search_fragment=True)))
    # Ordenar y paginar
    registros = consulta.order_by(UsuarioNomina.fecha.desc()).offset(start).limit(rows_per_page).all()
    total = consulta.count()
    # Elaborar datos para DataTable
    data = []
    for resultado in registros:
        data.append(
            {
                "detalle": {
                    "fecha": resultado.fecha.strftime("%Y-%m-%d"),
                    "descripcion": resultado.descripcion,
                },
                "usuario": {
                    "email": resultado.usuario.email,
                    "nombre": resultado.usuario.nombre,
                },
                "pdf": {
                    "archivo_pdf": resultado.archivo_pdf,
                    "url_pdf": url_for("usuarios_nominas.download_file_pdf", usuario_nomina_id=resultado.id),
                },
                "xml": {
                    "archivo_xml": resultado.archivo_xml,
                    "url_xml": url_for("usuarios_nominas.download_file_xml", usuario_nomina_id=resultado.id),
                },
            }
        )
    # Entregar JSON
    return output_datatable_json(draw, total, data)


@usuarios_nominas.route("/usuarios_nominas")
def list():
    """Listado de UsuarioNomina"""

    # Definir filtros por defecto, solo para el usuario actual
    filtros = {"usuario_id": current_user.id, "estatus": "A"}
    titulo = f"Recibos de Nómina de {current_user.nombre}"

    # Si es ADMINISTRADOR y viene usuario_id en la URL, agregar a los filtros
    if current_user.can_admin(MODULO):
        try:
            usuario_id = int(request.args.get("usuario_id"))
            usuario = Usuario.query.get_or_404(usuario_id)
            filtros = {"estatus": "A", "usuario_id": usuario_id}
            titulo = f"Recibos de Nómina de {usuario.nombre}"
        except (TypeError, ValueError):
            pass

    # Validar el CURP del Usuario, si NO tiene o es incorrecto se omite el listado y se muestra un mensaje
    mensaje_curp = ""
    try:
        safe_curp(current_user.curp)
    except ValueError:
        mensaje_curp = f"El CURP {current_user.curp} es incorrecto. Solicite por medio de un Ticket su corrección."

    # Entregar
    return render_template(
        "usuarios_nominas/list.jinja2",
        filtros=json.dumps(filtros),
        titulo=titulo,
        mensaje_curp=mensaje_curp,
        usuario_id=current_user.id,
    )


@usuarios_nominas.route("/usuarios_nominas//descargar_archivo_pdf/<int:usuario_nomina_id>/pdf")
def download_file_pdf(usuario_nomina_id):
    """Descargar el archivo PDF de un recibo de nomina"""

    # Consultar el Timbrado
    usuario_nomina = UsuarioNomina.query.get_or_404(usuario_nomina_id)

    # Seguridad de liga
    if usuario_nomina.usuario.curp != current_user.curp:
        raise NotFound("NO son iguales el CURP de su usuario al del recibo.")

    # Si no tiene URL, redirigir a la página de detalle
    if usuario_nomina.url_pdf == "":
        raise NotFound("Este recibo NO tiene un archivo PDF.")

    # Si no tiene nombre para el archivo en archivo_pdf, elaborar uno con el UUID
    descarga_nombre = usuario_nomina.archivo_pdf
    if descarga_nombre == "":
        descarga_nombre = f"{usuario_nomina.tfd_uuid}.pdf"

    # Obtener el contenido del archivo desde Google Storage
    try:
        descarga_contenido = get_file_from_gcs(
            bucket_name=current_app.config["CLOUD_STORAGE_DEPOSITO_PERSEO"],
            blob_name=get_blob_name_from_url(usuario_nomina.url_pdf),
        )
    except (MyBucketNotFoundError, MyFileNotFoundError, MyNotValidParamError) as error:
        raise NotFound("No se encontró el archivo PDF.")

    # Guardar en bitácora que se consultó su recibo de nómina
    Bitacora(
        modulo=Modulo.query.filter_by(nombre=MODULO).first(),
        usuario=current_user,
        descripcion=safe_message(f"Descargado recibo de nómina {usuario_nomina.archivo_pdf}"),
        url=url_for("usuarios_nominas.list"),
    ).save()

    # Descargar un archivo PDF
    response = make_response(descarga_contenido)
    response.headers["Content-Type"] = "application/pdf"
    response.headers["Content-Disposition"] = f"attachment; filename={descarga_nombre}"
    return response


@usuarios_nominas.route("/usuarios_nominas/descargar_archivo_xml/<int:usuario_nomina_id>/xml")
def download_file_xml(usuario_nomina_id):
    """Descargar el archivo XML de un recibo de nomina"""

    # Consultar el Timbrado
    usuario_nomina = UsuarioNomina.query.get_or_404(usuario_nomina_id)

    # Seguridad de liga
    if usuario_nomina.usuario.curp != current_user.curp:
        raise NotFound("NO son iguales el CURP de su usuario al del recibo.")

    # Si no tiene URL, redirigir a la página de detalle
    if usuario_nomina.url_xml == "":
        raise NotFound("Este recibo NO tiene un archivo XML.")

    # Si no tiene nombre para el archivo en archivo_xml, elaborar uno con el UUID
    descarga_nombre = usuario_nomina.archivo_xml
    if descarga_nombre == "":
        descarga_nombre = f"{usuario_nomina.tfd_uuid}.xml"

    # Obtener el contenido del archivo desde Google Storage
    try:
        descarga_contenido = get_file_from_gcs(
            bucket_name=current_app.config["CLOUD_STORAGE_DEPOSITO_PERSEO"],
            blob_name=get_blob_name_from_url(usuario_nomina.url_xml),
        )
    except (MyBucketNotFoundError, MyFileNotFoundError, MyNotValidParamError) as error:
        raise NotFound("No se encontró el archivo XML.")

    # Guardar en bitácora que se consultó su recibo de nómina
    Bitacora(
        modulo=Modulo.query.filter_by(nombre=MODULO).first(),
        usuario=current_user,
        descripcion=safe_message(f"Descargado recibo de nómina {usuario_nomina.archivo_xml}"),
        url=url_for("usuarios_nominas.list"),
    ).save()

    # Descargar un archivo XML
    response = make_response(descarga_contenido)
    response.headers["Content-Type"] = "text/xml"
    response.headers["Content-Disposition"] = f"attachment; filename={descarga_nombre}"
    return response
