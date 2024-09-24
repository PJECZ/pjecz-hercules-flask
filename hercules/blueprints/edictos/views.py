"""
Edictos, vistas
"""

import datetime
import json
import re
from urllib.parse import quote

from flask import Blueprint, current_app, flash, make_response, redirect, render_template, request, url_for
from flask_login import current_user, login_required
from werkzeug.datastructures import CombinedMultiDict
from werkzeug.exceptions import NotFound

from hercules.blueprints.autoridades.models import Autoridad
from hercules.blueprints.bitacoras.models import Bitacora
from hercules.blueprints.edictos.forms import EdictoEditForm, EdictoNewForm
from hercules.blueprints.edictos.models import Edicto
from hercules.blueprints.modulos.models import Modulo
from hercules.blueprints.permisos.models import Permiso
from hercules.blueprints.usuarios.decorators import permission_required
from lib.datatables import get_datatable_parameters, output_datatable_json
from lib.exceptions import (
    MyAnyError,
    MyBucketNotFoundError,
    MyFilenameError,
    MyFileNotFoundError,
    MyMissingConfigurationError,
    MyNotAllowedExtensionError,
    MyNotValidParamError,
    MyUnknownExtensionError,
)
from lib.google_cloud_storage import get_blob_name_from_url, get_file_from_gcs, get_media_type_from_filename
from lib.safe_string import safe_clave, safe_expediente, safe_message, safe_numero_publicacion, safe_string
from lib.storage import GoogleCloudStorage
from lib.time_to_text import dia_mes_ano

MODULO = "EDICTOS"
LIMITE_DIAS = 365  # Un anio
LIMITE_ADMINISTRADORES_DIAS = 3650  # Administradores pueden manipular diez anios
SUBDIRECTORIO = "edictos"

edictos = Blueprint("edictos", __name__, template_folder="templates")


@edictos.route("/edictos/acuses/<id_hashed>")
def checkout(id_hashed):
    """Acuse"""
    edicto = Edicto.query.get_or_404(Edicto.decode_id(id_hashed))
    dia, mes, anio = dia_mes_ano(edicto.creado)
    return render_template("edictos/print.jinja2", edicto=edicto, dia=dia, mes=mes.upper(), anio=anio)


@edictos.before_request
@login_required
@permission_required(MODULO, Permiso.VER)
def before_request():
    """Permiso por defecto"""


@edictos.route("/edictos/datatable_json", methods=["GET", "POST"])
def datatable_json():
    """DataTable JSON para listado de Edictos"""
    # Tomar parámetros de Datatables
    draw, start, rows_per_page = get_datatable_parameters()
    # Consultar
    consulta = Edicto.query
    # Primero filtrar por columnas propias
    if "estatus" in request.form:
        consulta = consulta.filter_by(estatus=request.form["estatus"])
    else:
        consulta = consulta.filter_by(estatus="A")
    if "autoridad_id" in request.form:
        autoridad = Autoridad.query.get(request.form["autoridad_id"])
        if autoridad:
            consulta = consulta.filter(Edicto.autoridad_id == autoridad.id)
    fecha_desde = None
    fecha_hasta = None
    if "fecha_desde" in request.form and re.match(r"\d{4}-\d{2}-\d{2}", request.form["fecha_desde"]):
        fecha_desde = request.form["fecha_desde"]
    if "fecha_hasta" in request.form and re.match(r"\d{4}-\d{2}-\d{2}", request.form["fecha_hasta"]):
        fecha_hasta = request.form["fecha_hasta"]
    if fecha_desde and fecha_hasta and fecha_desde > fecha_hasta:
        fecha_desde, fecha_hasta = fecha_hasta, fecha_desde
    if fecha_desde:
        consulta = consulta.filter(Edicto.fecha >= fecha_desde)
    if fecha_hasta:
        consulta = consulta.filter(Edicto.fecha <= fecha_hasta)
    if "descripcion" in request.form:
        descripcion = safe_string(request.form["descripcion"])
        if descripcion != "":
            consulta = consulta.filter(Edicto.descripcion.contains(descripcion))
    if "expediente" in request.form:
        try:
            expediente = safe_expediente(request.form["expediente"])
            consulta = consulta.filter_by(expediente=expediente)
        except (IndexError, ValueError):
            pass
    if "numero_publicacion" in request.form:
        try:
            numero_publicacion = safe_numero_publicacion(request.form["numero_publicacion"])
            consulta = consulta.filter_by(numero_publicacion=numero_publicacion)
        except (IndexError, ValueError):
            pass
    # Ordenar y paginar
    registros = consulta.order_by(Edicto.fecha.desc()).offset(start).limit(rows_per_page).all()
    total = consulta.count()
    # Elaborar datos para DataTable
    data = []
    for resultado in registros:
        data.append(
            {
                "fecha": resultado.fecha.strftime("%Y-%m-%d 00:00:00"),
                "detalle": {
                    "descripcion": resultado.descripcion,
                    "url": url_for("edictos.detail", edicto_id=resultado.id),
                },
                "expediente": resultado.expediente,
                "numero_publicacion": resultado.numero_publicacion,
                "archivo": {
                    "descargar_url": resultado.descargar_url,
                },
            }
        )
    # Entregar JSON
    return output_datatable_json(draw, total, data)


@edictos.route("/edictos/datatable_json_admin", methods=["GET", "POST"])
def datatable_json_admin():
    """DataTable JSON para listado de Edictos"""
    # Tomar parámetros de Datatables
    draw, start, rows_per_page = get_datatable_parameters()
    # Consultar
    consulta = Edicto.query
    # Primero filtrar por columnas propias
    if "estatus" in request.form:
        consulta = consulta.filter_by(estatus=request.form["estatus"])
    else:
        consulta = consulta.filter_by(estatus="A")
    if "autoridad_id" in request.form:
        autoridad = Autoridad.query.get(request.form["autoridad_id"])
        if autoridad:
            consulta = consulta.filter(Edicto.autoridad_id == autoridad.id)
    if "autoridad_clave" in request.form:
        try:
            autoridad_clave = safe_clave(request.form["autoridad_clave"])
            if autoridad_clave != "":
                consulta = consulta.join(Autoridad).filter(Autoridad.clave.contains(autoridad_clave))
        except ValueError:
            pass
    fecha_desde = None
    fecha_hasta = None
    if "fecha_desde" in request.form and re.match(r"\d{4}-\d{2}-\d{2}", request.form["fecha_desde"]):
        fecha_desde = request.form["fecha_desde"]
    if "fecha_hasta" in request.form and re.match(r"\d{4}-\d{2}-\d{2}", request.form["fecha_hasta"]):
        fecha_hasta = request.form["fecha_hasta"]
    if fecha_desde and fecha_hasta and fecha_desde > fecha_hasta:
        fecha_desde, fecha_hasta = fecha_hasta, fecha_desde
    if fecha_desde:
        consulta = consulta.filter(Edicto.fecha >= fecha_desde)
    if fecha_hasta:
        consulta = consulta.filter(Edicto.fecha <= fecha_hasta)
    if "descripcion" in request.form:
        descripcion = safe_string(request.form["descripcion"])
        if descripcion != "":
            consulta = consulta.filter(Edicto.descripcion.contains(descripcion))
    if "expediente" in request.form:
        try:
            expediente = safe_expediente(request.form["expediente"])
            consulta = consulta.filter_by(expediente=expediente)
        except (IndexError, ValueError):
            pass
    if "numero_publicacion" in request.form:
        try:
            numero_publicacion = safe_numero_publicacion(request.form["numero_publicacion"])
            consulta = consulta.filter_by(numero_publicacion=numero_publicacion)
        except (IndexError, ValueError):
            pass
    # Ordenar y paginar
    registros = consulta.order_by(Edicto.fecha.desc()).offset(start).limit(rows_per_page).all()
    total = consulta.count()
    # Elaborar datos para DataTable
    data = []
    for resultado in registros:
        data.append(
            {
                "creado": resultado.creado.strftime("%Y-%m-%d %H:%M:%S"),
                "autoridad": resultado.autoridad.clave,
                "fecha": resultado.fecha.strftime("%Y-%m-%d 00:00:00"),
                "detalle": {
                    "descripcion": resultado.descripcion,
                    "url": url_for("edictos.detail", edicto_id=resultado.id),
                },
                "expediente": resultado.expediente,
                "numero_publicacion": resultado.numero_publicacion,
                "archivo": {
                    "descargar_url": url_for("edictos.download", url=quote(resultado.url)),
                },
            }
        )
    # Entregar JSON
    return output_datatable_json(draw, total, data)


@edictos.route("/edictos")
def list_active():
    """Listado de Edictos activos"""
    # Si es administrador ve todo
    if current_user.can_admin("EDICTOS"):
        return render_template(
            "edictos/list_admin.jinja2",
            autoridad=None,
            filtros=json.dumps({"estatus": "A"}),
            titulo="Todos los Edictos",
            estatus="A",
        )
    # Si es jurisdiccional ve lo de su autoridad
    if current_user.autoridad.es_jurisdiccional:
        autoridad = current_user.autoridad
        return render_template(
            "edictos/list.jinja2",
            autoridad=autoridad,
            filtros=json.dumps({"autoridad_id": autoridad.id, "estatus": "A"}),
            titulo=f"Edictos de {autoridad.distrito.nombre_corto}, {autoridad.descripcion_corta}",
            estatus="A",
        )
    # Ninguno de los anteriores
    return redirect(url_for("edictos.list_distritos"))


@edictos.route("/edictos/inactivos")
@permission_required(MODULO, Permiso.ADMINISTRAR)
def list_inactive():
    """Listado de Edictos inactivos"""
    return render_template(
        "edictos/list.jinja2",
        filtros=json.dumps({"estatus": "B"}),
        titulo="Edictos inactivos",
        estatus="B",
    )


@edictos.route("/edictos/autoridad/<int:autoridad_id>")
def list_autoridad_edictos(autoridad_id):
    """Listado de Edictos activos de una autoridad"""
    autoridad = Autoridad.query.get_or_404(autoridad_id)
    if current_user.can_admin("EDICTOS"):
        plantilla = "edictos/list_admin.jinja2"
    else:
        plantilla = "edictos/list.jinja2"
    return render_template(
        plantilla,
        autoridad=autoridad,
        filtros=json.dumps({"autoridad_id": autoridad.id, "estatus": "A"}),
        titulo=f"Edictos de {autoridad.distrito.nombre_corto}, {autoridad.descripcion_corta}",
        estatus="A",
    )


@edictos.route("/edictos/inactivos/autoridad/<int:autoridad_id>")
@permission_required(MODULO, Permiso.ADMINISTRAR)
def list_autoridad_edictos_inactive(autoridad_id):
    """Listado de Edictos inactivos de una autoridad"""
    autoridad = Autoridad.query.get_or_404(autoridad_id)
    if current_user.can_admin("EDICTOS"):
        plantilla = "edictos/list_admin.jinja2"
    else:
        plantilla = "edictos/list.jinja2"
    return render_template(
        plantilla,
        autoridad=autoridad,
        filtros=json.dumps({"autoridad_id": autoridad.id, "estatus": "B"}),
        titulo=f"Edictos inactivos de {autoridad.distrito.nombre_corto}, {autoridad.descripcion_corta}",
        estatus="B",
    )


@edictos.route("/edictos/descargar", methods=["GET"])
@permission_required(MODULO, Permiso.ADMINISTRAR)
def download():
    """Descargar archivo desde Google Cloud Storage"""
    url = request.args.get("url")
    try:
        # Obtener nombre del blob
        blob_name = get_blob_name_from_url(url)
        # Obtener tipo de media
        media_type = get_media_type_from_filename(blob_name)
        # Obtener archivo
        archivo = get_file_from_gcs(current_app.config["CLOUD_STORAGE_DEPOSITO_EDICTOS"], blob_name)
    except MyAnyError as error:
        flash(str(error), "warning")
        return redirect(url_for("edictos.list_active"))
    # Entregar archivo
    return current_app.response_class(archivo, mimetype=media_type)


@edictos.route("/edictos/<int:edicto_id>")
def detail(edicto_id):
    """Detalle de un Edicto"""
    edicto = Edicto.query.get_or_404(edicto_id)
    return render_template("edictos/detail.jinja2", edicto=edicto)


def new_success(edicto):
    """Mensaje de éxito en nuevo edicto"""
    piezas = ["Nuevo edicto"]
    if edicto.expediente != "":
        piezas.append(f"expediente {edicto.expediente},")
    if edicto.numero_publicacion != "":
        piezas.append(f"número {edicto.numero_publicacion},")
    piezas.append(f"fecha {edicto.fecha.strftime('%Y-%m-%d')} de {edicto.autoridad.clave}")
    bitacora = Bitacora(
        modulo=Modulo.query.filter_by(nombre=MODULO).first(),
        usuario=current_user,
        descripcion=safe_message(" ".join(piezas)),
        url=url_for("edictos.detail", edicto_id=edicto.id),
    )
    bitacora.save()
    return bitacora


@edictos.route("/edictos/nuevo", methods=["GET", "POST"])
@permission_required(MODULO, Permiso.CREAR)
def new():
    """Nuevo Edicto como juzgado"""
    # Para validar la fecha
    hoy = datetime.date.today()
    hoy_dt = datetime.datetime(year=hoy.year, month=hoy.month, day=hoy.day)
    limite_dt = hoy_dt + datetime.timedelta(days=-LIMITE_DIAS)

    # Validar autoridad
    autoridad = current_user.autoridad
    if autoridad is None or autoridad.estatus != "A":
        flash("El juzgado/autoridad no existe o no es activa.", "warning")
        return redirect(url_for("edictos.list_active"))
    if not autoridad.distrito.es_distrito_judicial:
        flash("El juzgado/autoridad no está en un distrito jurisdiccional.", "warning")
        return redirect(url_for("edictos.list_active"))
    if not autoridad.es_jurisdiccional:
        flash("El juzgado/autoridad no es jurisdiccional.", "warning")
        return redirect(url_for("edictos.list_active"))
    if autoridad.directorio_edictos is None or autoridad.directorio_edictos == "":
        flash("El juzgado/autoridad no tiene directorio para edictos.", "warning")
        return redirect(url_for("edictos.list_active"))

    # Si viene el formulario
    form = EdictoNewForm(CombinedMultiDict((request.files, request.form)))
    if form.validate_on_submit():
        es_valido = True

        # Validar fecha
        fecha = form.fecha.data
        if not limite_dt <= datetime.datetime(year=fecha.year, month=fecha.month, day=fecha.day) <= hoy_dt:
            flash(f"La fecha no debe ser del futuro ni anterior a {LIMITE_DIAS} días.", "warning")
            form.fecha.data = hoy
            es_valido = False

        # Validar descripcion
        descripcion = safe_string(form.descripcion.data)
        if descripcion == "":
            flash("La descripción es incorrecta.", "warning")
            es_valido = False

        # Validar expediente
        try:
            expediente = safe_expediente(form.expediente.data)
        except (IndexError, ValueError):
            flash("El expediente es incorrecto.", "warning")
            es_valido = False

        # Validar número de publicación
        try:
            numero_publicacion = safe_numero_publicacion(form.numero_publicacion.data)
        except (IndexError, ValueError):
            flash("El número de publicación es incorrecto.", "warning")
            es_valido = False

        # Validar archivo
        archivo = request.files["archivo"]
        storage = GoogleCloudStorage(base_directory=SUBDIRECTORIO, allowed_extensions=["pdf"])
        try:
            storage.set_content_type(archivo.filename)
        except MyNotAllowedExtensionError:
            flash("Tipo de archivo no permitido.", "warning")
            es_valido = False
        except MyUnknownExtensionError:
            flash("Tipo de archivo desconocido.", "warning")
            es_valido = False

        # No es válido, entonces se vuelve a mostrar el formulario
        if es_valido is False:
            return render_template("edictos/new.jinja2", form=form)

        edicto = Edicto(
            autoridad=autoridad,
            fecha=fecha,
            descripcion=descripcion,
            expediente=expediente,
            numero_publicacion=numero_publicacion,
        )
        edicto.save()

        # Subir a Google Cloud Storage
        es_exitoso = True
        try:
            storage.set_filename(hashed_id=edicto.encode_id(), description=descripcion)
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

        # Si se sube con exito, actualizar el registro con la URL del archivo y mostrar el detalle
        if es_exitoso:
            edicto.archivo = storage.filename  # Conservar el nombre original
            edicto.url = storage.url
            edicto.save()
            bitacora = new_success(edicto)
            flash(bitacora.descripcion, "success")
            return redirect(bitacora.url)

        # Como no se subio con exito, se cambia el estatus a "B"
        edicto.estatus = "B"
        edicto.save()
    # Pre-llenado de los campos
    form.distrito.data = autoridad.distrito.nombre
    form.autoridad.data = autoridad.descripcion
    form.fecha.data = hoy
    return render_template("edictos/new.jinja2", form=form)


@edictos.route("/edictos/nuevo/<int:autoridad_id>", methods=["GET", "POST"])
@permission_required(MODULO, Permiso.ADMINISTRAR)
def new_for_autoridad(autoridad_id):
    """Subir Edicto para una autoridad dada"""

    # Para validar la fecha
    hoy = datetime.date.today()
    hoy_dt = datetime.datetime(year=hoy.year, month=hoy.month, day=hoy.day)
    limite_dt = hoy_dt + datetime.timedelta(days=-LIMITE_ADMINISTRADORES_DIAS)

    # Validar autoridad
    autoridad = Autoridad.query.get_or_404(autoridad_id)
    if autoridad is None:
        flash("El juzgado/autoridad no existe.", "warning")
        return redirect(url_for("edictos.list_active"))
    if autoridad.estatus != "A":
        flash("El juzgado/autoridad no es activa.", "warning")
        return redirect(url_for("autoridades.detail", autoridad_id=autoridad.id))
    if not autoridad.distrito.es_distrito_judicial:
        flash("El juzgado/autoridad no está en un distrito jurisdiccional.", "warning")
        return redirect(url_for("autoridades.detail", autoridad_id=autoridad.id))
    if not autoridad.es_jurisdiccional:
        flash("El juzgado/autoridad no es jurisdiccional.", "warning")
        return redirect(url_for("autoridades.detail", autoridad_id=autoridad.id))
    if autoridad.directorio_edictos is None or autoridad.directorio_edictos == "":
        flash("El juzgado/autoridad no tiene directorio para edictos.", "warning")
        return redirect(url_for("autoridades.detail", autoridad_id=autoridad.id))

    # Si viene el formulario
    form = EdictoNewForm(CombinedMultiDict((request.files, request.form)))
    if form.validate_on_submit():
        es_valido = True

        # Validar fecha
        fecha = form.fecha.data
        if not limite_dt <= datetime.datetime(year=fecha.year, month=fecha.month, day=fecha.day) <= hoy_dt:
            flash(f"La fecha no debe ser del futuro ni anterior a {LIMITE_ADMINISTRADORES_DIAS} días.", "warning")
            form.fecha.data = hoy
            es_valido = False

        # Validar descripcion
        descripcion = safe_string(form.descripcion.data)
        if descripcion == "":
            flash("La descripción es incorrecta.", "warning")
            es_valido = False

        # Validar expediente
        try:
            expediente = safe_expediente(form.expediente.data)
        except (IndexError, ValueError):
            flash("El expediente es incorrecto.", "warning")
            es_valido = False

        # Validar número de publicación
        try:
            numero_publicacion = safe_numero_publicacion(form.numero_publicacion.data)
        except (IndexError, ValueError):
            flash("El número de publicación es incorrecto.", "warning")
            es_valido = False

        # Validar archivo
        archivo = request.files["archivo"]
        storage = GoogleCloudStorage(base_directory=SUBDIRECTORIO, allowed_extensions=["pdf"])
        try:
            storage.set_content_type(archivo.filename)
        except MyNotAllowedExtensionError:
            flash("Tipo de archivo no permitido.", "warning")
            es_valido = False
        except MyUnknownExtensionError:
            flash("Tipo de archivo desconocido.", "warning")
            es_valido = False

        # No es válido, entonces se vuelve a mostrar el formulario
        if es_valido is False:
            return render_template("edictos/new_for_autoridad.jinja2", form=form, autoridad=autoridad)

        # Insertar registro
        edicto = Edicto(
            autoridad=autoridad,
            fecha=fecha,
            descripcion=descripcion,
            expediente=expediente,
            numero_publicacion=numero_publicacion,
        )
        edicto.save()

        # Subir a Google Cloud Storage
        es_exitoso = True
        try:
            storage.set_filename(hashed_id=edicto.encode_id(), description=descripcion)
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

        # Si se sube con exito, actualizar el registro con la URL del archivo y mostrar el detalle
        if es_exitoso:
            edicto.archivo = storage.filename  # Conservar el nombre original
            edicto.url = storage.url
            edicto.save()
            bitacora = new_success(edicto)
            flash(bitacora.descripcion, "success")
            return redirect(bitacora.url)

        # Como no se subio con exito, se cambia el estatus a "B"
        edicto.estatus = "B"
        edicto.save()
    # Prellenado de los campos
    form.distrito.data = autoridad.distrito.nombre
    form.autoridad.data = autoridad.descripcion
    form.fecha.data = hoy
    return render_template("edictos/new_for_autoridad.jinja2", form=form, autoridad=autoridad)


def edit_success(edicto):
    """Mensaje de éxito al editar un edicto"""
    piezas = ["Editado edicto"]
    if edicto.expediente != "":
        piezas.append(f"expediente {edicto.expediente},")
    if edicto.numero_publicacion != "":
        piezas.append(f"número {edicto.numero_publicacion},")
    piezas.append(f"fecha {edicto.fecha.strftime('%Y-%m-%d')} de {edicto.autoridad.clave}")
    bitacora = Bitacora(
        modulo=Modulo.query.filter_by(nombre=MODULO).first(),
        usuario=current_user,
        descripcion=safe_message(" ".join(piezas)),
        url=url_for("edictos.detail", edicto_id=edicto.id),
    )
    bitacora.save()
    return bitacora


@edictos.route("/edictos/edicion/<int:edicto_id>", methods=["GET", "POST"])
@permission_required(MODULO, Permiso.MODIFICAR)
def edit(edicto_id):
    """Editar Edicto"""

    # Validar edicto
    edicto = Edicto.query.get_or_404(edicto_id)
    if not (current_user.can_admin("EDICTOS") or current_user.autoridad_id == edicto.autoridad_id):
        flash("No tiene permiso para editar este edicto.", "warning")
        return redirect(url_for("edictos.list_active"))

    form = EdictoEditForm()
    if form.validate_on_submit():
        es_valido = True
        edicto.fecha = form.fecha.data

        # Validar descripción
        edicto.descripcion = safe_string(form.descripcion.data)
        if edicto.descripcion == "":
            flash("La descripción es incorrecta.", "warning")
            es_valido = False

        # Validar expediente
        try:
            edicto.expediente = safe_expediente(form.expediente.data)
        except (IndexError, ValueError):
            flash("El expediente es incorrecto.", "warning")
            es_valido = False

        # Validar número de publicación
        try:
            edicto.numero_publicacion = safe_numero_publicacion(form.numero_publicacion.data)
        except (IndexError, ValueError):
            flash("El número de publicación es incorrecto.", "warning")
            es_valido = False

        if es_valido:
            edicto.save()
            bitacora = edit_success(edicto)
            flash(bitacora.descripcion, "success")
            return redirect(bitacora.url)

    form.fecha.data = edicto.fecha
    form.descripcion.data = edicto.descripcion
    form.expediente.data = edicto.expediente
    form.numero_publicacion.data = edicto.numero_publicacion
    return render_template("edictos/edit.jinja2", form=form, edicto=edicto)


@edictos.route("/edictos/eliminar/<int:edicto_id>")
@permission_required(MODULO, Permiso.ADMINISTRAR)
def delete(edicto_id):
    """Eliminar Edicto"""
    edicto = Edicto.query.get_or_404(edicto_id)
    if edicto.estatus == "A":
        edicto.delete()
        bitacora = Bitacora(
            modulo=Modulo.query.filter_by(nombre=MODULO).first(),
            usuario=current_user,
            descripcion=safe_message(f"Eliminado Edicto {edicto.descripcion}"),
            url=url_for("edictos.detail", edicto_id=edicto.id),
        )
        bitacora.save()
        flash(bitacora.descripcion, "success")
    return redirect(url_for("edictos.detail", edicto_id=edicto.id))


@edictos.route("/edictos/recuperar/<int:edicto_id>")
@permission_required(MODULO, Permiso.ADMINISTRAR)
def recover(edicto_id):
    """Recuperar Edicto"""
    edicto = Edicto.query.get_or_404(edicto_id)
    if edicto.estatus == "B":
        edicto.recover()
        bitacora = Bitacora(
            modulo=Modulo.query.filter_by(nombre=MODULO).first(),
            usuario=current_user,
            descripcion=safe_message(f"Recuperado Edicto {edicto.descripcion}"),
            url=url_for("edictos.detail", edicto_id=edicto.id),
        )
        bitacora.save()
        flash(bitacora.descripcion, "success")
    return redirect(url_for("edictos.detail", edicto_id=edicto.id))


@edictos.route("/edictos/ver_archivo_pdf/<int:edicto_id>")
def view_file_pdf(edicto_id):
    """Ver archivo PDF de Edicto para insertarlo en un iframe en el detalle"""

    # Consultar la edicto
    edicto = Edicto.query.get_or_404(edicto_id)

    # Obtener el contenido del archivo
    try:
        archivo = get_file_from_gcs(
            bucket_name=current_app.config["CLOUD_STORAGE_DEPOSITO_EDICTOS"],
            blob_name=get_blob_name_from_url(edicto.url),
        )
    except (MyBucketNotFoundError, MyFileNotFoundError, MyNotValidParamError) as error:
        raise NotFound("No se encontró el archivo.") from error

    # Entregar el archivo
    response = make_response(archivo)
    response.headers["Content-Type"] = "application/pdf"
    return response
