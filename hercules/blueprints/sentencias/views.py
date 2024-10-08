"""
Sentencias, vistas
"""

import json
import re
from datetime import date, datetime, timedelta
from urllib.parse import quote

from flask import Blueprint, current_app, flash, make_response, redirect, render_template, request, url_for
from flask_login import current_user, login_required
from pytz import timezone
from sqlalchemy.sql.functions import count
from werkzeug.datastructures import CombinedMultiDict
from werkzeug.exceptions import NotFound

from hercules.blueprints.autoridades.models import Autoridad
from hercules.blueprints.bitacoras.models import Bitacora
from hercules.blueprints.materias.models import Materia
from hercules.blueprints.materias_tipos_juicios.models import MateriaTipoJuicio
from hercules.blueprints.modulos.models import Modulo
from hercules.blueprints.permisos.models import Permiso
from hercules.blueprints.sentencias.forms import SentenciaEditForm, SentenciaNewForm, SentenciaReportForm
from hercules.blueprints.sentencias.models import Sentencia
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
from lib.safe_string import (
    extract_expediente_anio,
    extract_expediente_num,
    safe_clave,
    safe_expediente,
    safe_message,
    safe_sentencia,
    safe_string,
)
from lib.storage import GoogleCloudStorage
from lib.time_to_text import dia_mes_ano

# Zona horaria
TIMEZONE = "America/Mexico_City"
local_tz = timezone(TIMEZONE)

# Constantes de este módulo
MODULO = "SENTENCIAS"
LIMITE_DIAS = 365  # Un anio
LIMITE_ADMINISTRADORES_DIAS = 7300  # Administradores pueden manipular veinte anios
ROL_REPORTES_TODOS = ["ADMINISTRADOR", "ESTADISTICA", "VISITADURIA JUDICIAL"]  # Roles que deben estar en la BD

sentencias = Blueprint("sentencias", __name__, template_folder="templates")


@sentencias.before_request
@login_required
@permission_required(MODULO, Permiso.VER)
def before_request():
    """Permiso por defecto"""


@sentencias.route("/sentencias/acuses/<id_hashed>")
def checkout(id_hashed):
    """Acuse"""
    sentencia = Sentencia.query.get_or_404(Sentencia.decode_id(id_hashed))
    dia, mes, ano = dia_mes_ano(sentencia.creado)
    return render_template("sentencias/checkout.jinja2", sentencia=sentencia, dia=dia, mes=mes.upper(), ano=ano)


@sentencias.route("/sentencias/datatable_json", methods=["GET", "POST"])
def datatable_json():
    """DataTable JSON con Sentencias"""

    # Tomar parámetros de Datatables
    draw, start, rows_per_page = get_datatable_parameters()

    # Consultar
    consulta = Sentencia.query

    # Primero filtrar por columnas propias
    if "estatus" in request.form:
        consulta = consulta.filter(Sentencia.estatus == request.form["estatus"])
    else:
        consulta = consulta.filter(Sentencia.estatus == "A")
    if "autoridad_id" in request.form:
        autoridad = Autoridad.query.get(request.form["autoridad_id"])
        if autoridad:
            consulta = consulta.filter(Sentencia.autoridad_id == autoridad.id)
    elif "autoridad_clave" in request.form:
        autoridad_clave = safe_clave(request.form["autoridad_clave"])
        if autoridad_clave != "":
            consulta = consulta.join(Autoridad).filter(Autoridad.clave.contains(autoridad_clave))
    if "materia_tipo_juicio_id" in request.form:
        materia_tipo_juicio = MateriaTipoJuicio.query.get(request.form["materia_tipo_juicio_id"])
        if materia_tipo_juicio:
            consulta = consulta.filter(Sentencia.materia_tipo_juicio_id == materia_tipo_juicio.id)
    elif "materia_tipo_juicio_descripcion" in request.form:
        materia_tipo_juicio_descripcion = safe_string(request.form["materia_tipo_juicio_descripcion"], save_enie=True)
        if materia_tipo_juicio_descripcion != "":
            consulta = consulta.join(MateriaTipoJuicio).filter(
                MateriaTipoJuicio.descripcion.contains(materia_tipo_juicio_descripcion)
            )
    if "descripcion" in request.form:
        descripcion = safe_string(request.form["descripcion"], save_enie=True)
        if descripcion != "":
            consulta = consulta.filter(Sentencia.descripcion.contains(descripcion))
    if "sentencia" in request.form:
        try:
            sentencia = safe_sentencia(request.form["sentencia"])
            consulta = consulta.filter(Sentencia.sentencia == sentencia)
        except (IndexError, ValueError):
            pass
    if "expediente" in request.form:
        try:
            expediente = safe_expediente(request.form["expediente"])
            consulta = consulta.filter(Sentencia.expediente == expediente)
        except (IndexError, ValueError):
            pass

    # Filtrar por fechas, si vienen invertidas se corrigen
    fecha_desde = None
    fecha_hasta = None
    if "fecha_desde" in request.form and re.match(r"\d{4}-\d{2}-\d{2}", request.form["fecha_desde"]):
        fecha_desde = request.form["fecha_desde"]
    if "fecha_hasta" in request.form and re.match(r"\d{4}-\d{2}-\d{2}", request.form["fecha_hasta"]):
        fecha_hasta = request.form["fecha_hasta"]
    if fecha_desde and fecha_hasta and fecha_desde > fecha_hasta:
        fecha_desde, fecha_hasta = fecha_hasta, fecha_desde
    if fecha_desde:
        consulta = consulta.filter(Sentencia.fecha >= fecha_desde)
    if fecha_hasta:
        consulta = consulta.filter(Sentencia.fecha <= fecha_hasta)

    # Ordenar y paginar
    registros = consulta.order_by(Sentencia.id.desc()).offset(start).limit(rows_per_page).all()
    total = consulta.count()

    # Elaborar datos para DataTable
    data = []
    for sentencia in registros:
        data.append(
            {
                "fecha": sentencia.fecha.strftime("%Y-%m-%d 00:00:00"),
                "autoridad_clave": sentencia.autoridad.clave,
                "detalle": {
                    "sentencia": sentencia.sentencia,
                    "url": url_for("sentencias.detail", sentencia_id=sentencia.id),
                },
                "expediente": sentencia.expediente,
                "materia_nombre": sentencia.materia_tipo_juicio.materia.nombre,
                "materia_tipo_juicio_descripcion": sentencia.materia_tipo_juicio.descripcion,
                "es_perspectiva_genero": "Sí" if sentencia.es_perspectiva_genero else "",
                "creado": sentencia.creado.astimezone(local_tz).strftime("%Y-%m-%d %H:%M"),
            }
        )

    # Entregar JSON
    return output_datatable_json(draw, total, data)


@sentencias.route("/sentencias/admin_datatable_json", methods=["GET", "POST"])
def admin_datatable_json():
    """DataTable JSON con Sentencias para administrador"""

    # Tomar parámetros de Datatables
    draw, start, rows_per_page = get_datatable_parameters()

    # Consultar
    consulta = Sentencia.query

    # Primero filtrar por columnas propias
    if "estatus" in request.form:
        consulta = consulta.filter(Sentencia.estatus == request.form["estatus"])
    else:
        consulta = consulta.filter(Sentencia.estatus == "A")
    if "autoridad_id" in request.form:
        autoridad = Autoridad.query.get(request.form["autoridad_id"])
        if autoridad:
            consulta = consulta.filter(Sentencia.autoridad_id == autoridad.id)
    elif "autoridad_clave" in request.form:
        autoridad_clave = safe_clave(request.form["autoridad_clave"])
        if autoridad_clave != "":
            consulta = consulta.join(Autoridad).filter(Autoridad.clave.contains(autoridad_clave))
    if "materia_tipo_juicio_id" in request.form:
        materia_tipo_juicio = MateriaTipoJuicio.query.get(request.form["materia_tipo_juicio_id"])
        if materia_tipo_juicio:
            consulta = consulta.filter(Sentencia.materia_tipo_juicio_id == materia_tipo_juicio.id)
    elif "materia_tipo_juicio_descripcion" in request.form:
        materia_tipo_juicio_descripcion = safe_string(request.form["materia_tipo_juicio_descripcion"], save_enie=True)
        if materia_tipo_juicio_descripcion != "":
            consulta = consulta.join(MateriaTipoJuicio).filter(
                MateriaTipoJuicio.descripcion.contains(materia_tipo_juicio_descripcion)
            )
    if "descripcion" in request.form:
        descripcion = safe_string(request.form["descripcion"], save_enie=True)
        if descripcion != "":
            consulta = consulta.filter(Sentencia.descripcion.contains(descripcion))
    if "sentencia" in request.form:
        try:
            sentencia = safe_sentencia(request.form["sentencia"])
            consulta = consulta.filter(Sentencia.sentencia == sentencia)
        except (IndexError, ValueError):
            pass
    if "expediente" in request.form:
        try:
            expediente = safe_expediente(request.form["expediente"])
            consulta = consulta.filter(Sentencia.expediente == expediente)
        except (IndexError, ValueError):
            pass

    # Filtrar por fechas, si vienen invertidas se corrigen
    fecha_desde = None
    fecha_hasta = None
    if "fecha_desde" in request.form and re.match(r"\d{4}-\d{2}-\d{2}", request.form["fecha_desde"]):
        fecha_desde = request.form["fecha_desde"]
    if "fecha_hasta" in request.form and re.match(r"\d{4}-\d{2}-\d{2}", request.form["fecha_hasta"]):
        fecha_hasta = request.form["fecha_hasta"]
    if fecha_desde and fecha_hasta and fecha_desde > fecha_hasta:
        fecha_desde, fecha_hasta = fecha_hasta, fecha_desde
    if fecha_desde:
        consulta = consulta.filter(Sentencia.fecha >= fecha_desde)
    if fecha_hasta:
        consulta = consulta.filter(Sentencia.fecha <= fecha_hasta)

    # Ordenar y paginar
    registros = consulta.order_by(Sentencia.id.desc()).offset(start).limit(rows_per_page).all()
    total = consulta.count()

    # Elaborar datos para DataTable
    data = []
    for sentencia in registros:
        data.append(
            {
                "detalle": {
                    "id": sentencia.id,
                    "url": url_for("sentencias.detail", sentencia_id=sentencia.id),
                },
                "creado": sentencia.creado.astimezone(local_tz).strftime("%Y-%m-%d %H:%M"),
                "autoridad": sentencia.autoridad.clave,
                "fecha": sentencia.fecha.strftime("%Y-%m-%d"),
                "sentencia": sentencia.sentencia,
                "expediente": sentencia.expediente,
                "materia_nombre": sentencia.materia_tipo_juicio.materia.nombre,
                "materia_tipo_juicio_descripcion": sentencia.materia_tipo_juicio.descripcion,
                "es_perspectiva_genero": "Sí" if sentencia.es_perspectiva_genero else "",
            }
        )

    # Entregar JSON
    return output_datatable_json(draw, total, data)


@sentencias.route("/sentencias")
def list_active():
    """Listado de Sentencias activos"""

    # Definir valores por defecto
    plantilla = "sentencias/list.jinja2"
    filtros = None
    titulo = None
    autoridad = None

    # Si es administrador
    if current_user.can_admin(MODULO):
        plantilla = "sentencias/list_admin.jinja2"

    # Si viene autoridad_id o autoridad_clave en la URL, agregar a los filtros
    try:
        if "autoridad_id" in request.args:
            autoridad_id = int(request.args.get("autoridad_id"))
            autoridad = Autoridad.query.get(autoridad_id)
        elif "autoridad_clave" in request.args:
            autoridad_clave = safe_clave(request.args.get("autoridad_clave"))
            autoridad = Autoridad.query.filter_by(clave=autoridad_clave).first()
        if autoridad is not None:
            filtros = {"estatus": "A", "autoridad_id": autoridad.id}
            titulo = f"V.P. de Sentencias de {autoridad.descripcion_corta}"
    except (TypeError, ValueError):
        pass

    # Si es administrador
    if titulo is None and current_user.can_admin(MODULO):
        titulo = "Todos las V.P. de Sentencias"
        filtros = {"estatus": "A"}

    # Si puede editar o crear, solo ve lo de su autoridad
    if titulo is None and (current_user.can_insert(MODULO) or current_user.can_edit(MODULO)):
        autoridad = None  # Para no mostrar el botón 'Todos los...'
        filtros = {"estatus": "A", "autoridad_id": current_user.autoridad.id}
        titulo = f"Versión Pública de Sentencias de {current_user.autoridad.descripcion_corta}"

    # De lo contrario, es observador
    if titulo is None:
        autoridad = None
        filtros = {"estatus": "A"}
        titulo = "Versión Pública de Sentencias"

    # Entregar
    return render_template(
        plantilla,
        filtros=json.dumps(filtros),
        titulo=titulo,
        estatus="A",
        autoridad=autoridad,
    )


@sentencias.route("/sentencias/inactivos")
@permission_required(MODULO, Permiso.ADMINISTRAR)
def list_inactive():
    """Listado de Sentencias inactivas"""
    # Solo los administradores ven todas las sentencias inactivas
    return render_template(
        "sentencias/list_admin.jinja2",
        filtros=json.dumps({"estatus": "B"}),
        titulo="Todas las V.P. de Sentencias inactivas",
        estatus="B",
    )


@sentencias.route("/sentencias/<int:sentencia_id>")
def detail(sentencia_id):
    """Detalle de un Sentencia"""
    sentencia = Sentencia.query.get_or_404(sentencia_id)
    return render_template("sentencias/detail.jinja2", sentencia=sentencia)


@sentencias.route("/sentencias/nuevo", methods=["GET", "POST"])
@permission_required(MODULO, Permiso.CREAR)
def new():
    """Subir Sentencia como juzgado"""

    # Validar autoridad
    autoridad = current_user.autoridad
    if autoridad is None or autoridad.estatus != "A":
        flash("El juzgado/autoridad no existe o no es activa.", "warning")
        return redirect(url_for("sentencias.list_active"))
    if not autoridad.distrito.es_distrito_judicial:
        flash("El juzgado/autoridad no está en un distrito jurisdiccional.", "warning")
        return redirect(url_for("sentencias.list_active"))
    if not autoridad.es_jurisdiccional:
        flash("El juzgado/autoridad no es jurisdiccional.", "warning")
        return redirect(url_for("sentencias.list_active"))
    if autoridad.directorio_sentencias is None or autoridad.directorio_sentencias == "":
        flash("El juzgado/autoridad no tiene directorio para sentencias.", "warning")
        return redirect(url_for("sentencias.list_active"))

    # Definir la fecha límite para el juzgado
    hoy = date.today()
    hoy_dt = datetime(year=hoy.year, month=hoy.month, day=hoy.day)
    limite_dt = hoy_dt + timedelta(days=-LIMITE_DIAS)

    # Si viene el formulario
    form = SentenciaNewForm(CombinedMultiDict((request.files, request.form)))
    if form.validate_on_submit():
        es_valido = True

        # Validar fecha
        fecha = form.fecha.data
        if not limite_dt <= datetime(year=fecha.year, month=fecha.month, day=fecha.day) <= hoy_dt:
            flash(f"La fecha no debe ser del futuro ni anterior a {LIMITE_DIAS} días.", "warning")
            es_valido = False

        # Validar sentencia
        try:
            sentencia_input = safe_sentencia(form.sentencia.data)
        except (IndexError, ValueError):
            flash("La sentencia es incorrecta.", "warning")
            es_valido = False

        # Validar sentencia_fecha
        sentencia_fecha = form.sentencia_fecha.data
        if not limite_dt <= datetime(year=sentencia_fecha.year, month=sentencia_fecha.month, day=sentencia_fecha.day) <= hoy_dt:
            flash(f"La fecha de la sentencia no debe ser del futuro ni anterior a {LIMITE_DIAS} días.", "warning")
            es_valido = False

        # Validar expediente
        try:
            expediente = safe_expediente(form.expediente.data)
        except (IndexError, ValueError):
            flash("El expediente es incorrecto.", "warning")
            es_valido = False

        # Tomar tipo de juicio
        materia_tipo_juicio = MateriaTipoJuicio.query.get(form.materia_tipo_juicio.data)

        # Tomar descripcion
        descripcion = safe_string(form.descripcion.data, max_len=1000)

        # Tomar perspectiva de género
        es_perspectiva_genero = form.es_perspectiva_genero.data  # Boleano

        # Inicializar la liberia GCS con el directorio base, la fecha, las extensiones y los meses como palabras
        gcstorage = GoogleCloudStorage(
            base_directory=autoridad.directorio_sentencias,
            upload_date=fecha,
            allowed_extensions=["pdf"],
            month_in_word=True,
            bucket_name=current_app.config["CLOUD_STORAGE_DEPOSITO_SENTENCIAS"],
        )

        # Validar archivo
        archivo = request.files["archivo"]
        try:
            gcstorage.set_content_type(archivo.filename)
        except MyNotAllowedExtensionError:
            flash("Tipo de archivo no permitido.", "warning")
            es_valido = False
        except MyUnknownExtensionError:
            flash("Tipo de archivo desconocido.", "warning")
            es_valido = False

        # Si es valido
        if es_valido:
            # Insertar registro
            sentencia = Sentencia(
                autoridad=autoridad,
                materia_tipo_juicio=materia_tipo_juicio,
                sentencia=sentencia_input,
                sentencia_fecha=sentencia_fecha,
                expediente=expediente,
                expediente_anio=extract_expediente_anio(expediente),
                expediente_num=extract_expediente_num(expediente),
                fecha=fecha,
                descripcion=descripcion,
                es_perspectiva_genero=es_perspectiva_genero,
            )
            sentencia.save()

            # El nombre del archivo contiene FECHA/SENTENCIA/EXPEDIENTE/PERSPECTIVA_GENERO/HASH
            nombre_elementos = []
            nombre_elementos.append(sentencia_input.replace("/", "-"))
            nombre_elementos.append(expediente.replace("/", "-"))
            if es_perspectiva_genero:
                nombre_elementos.append("G")

            # Subir a Google Cloud Storage
            es_exitoso = True
            try:
                gcstorage.set_filename(hashed_id=sentencia.encode_id(), description="-".join(nombre_elementos))
                gcstorage.upload(archivo.stream.read())
            except (MyFilenameError, MyNotAllowedExtensionError, MyUnknownExtensionError):
                flash("Error fatal al subir el archivo a GCS.", "warning")
                es_exitoso = False
            except MyMissingConfigurationError:
                flash("Error al subir el archivo porque falla la configuración de GCS.", "danger")
                es_exitoso = False
            except Exception:
                flash("Error desconocido al subir el archivo.", "danger")
                es_exitoso = False

            # Si se sube con éxito, actualizar el registro con la URL del archivo y mostrar el detalle
            if es_exitoso:
                sentencia.archivo = gcstorage.filename  # Conservar el nombre original
                sentencia.url = gcstorage.url
                sentencia.save()
                bitacora = Bitacora(
                    modulo=Modulo.query.filter_by(nombre=MODULO).first(),
                    usuario=current_user,
                    descripcion=safe_message(
                        f"Nueva Sentencia de {autoridad.clave} con sentencia {sentencia.sentencia} y del expediente {sentencia.expediente}"
                    ),
                    url=url_for("sentencias.detail", sentencia_id=sentencia.id),
                )
                bitacora.save()
                flash(bitacora.descripcion, "success")
                return redirect(bitacora.url)

            # Como no se subio con exito, se cambia el estatus a "B"
            sentencia.estatus = "B"
            sentencia.save()

    # Llenar de los campos del formulario
    form.distrito.data = autoridad.distrito.nombre
    form.autoridad.data = autoridad.descripcion
    form.fecha.data = hoy

    # Entregar el formulario
    return render_template(
        "sentencias/new.jinja2",
        form=form,
        autoridad=autoridad,
        materias=Materia.query.filter_by(en_sentencias=True).filter_by(estatus="A").order_by(Materia.id).all(),
        materias_tipos_juicios=MateriaTipoJuicio.query.filter_by(estatus="A")
        .order_by(MateriaTipoJuicio.materia_id, MateriaTipoJuicio.descripcion)
        .all(),
    )


@sentencias.route("/sentencias/nuevo/<int:autoridad_id>", methods=["GET", "POST"])
@permission_required(MODULO, Permiso.ADMINISTRAR)
def new_with_autoridad_id(autoridad_id):
    """Subir Sentencia para una autoridad como administrador"""

    # Validar autoridad
    autoridad = Autoridad.query.get_or_404(autoridad_id)
    if autoridad is None:
        flash("El juzgado/autoridad no existe.", "warning")
        return redirect(url_for("sentencias.list_active"))
    if autoridad.estatus != "A":
        flash("El juzgado/autoridad no es activa.", "warning")
        return redirect(url_for("autoridades.detail", autoridad_id=autoridad.id))
    if not autoridad.distrito.es_distrito_judicial:
        flash("El juzgado/autoridad no está en un distrito jurisdiccional.", "warning")
        return redirect(url_for("autoridades.detail", autoridad_id=autoridad.id))
    if not autoridad.es_jurisdiccional:
        flash("El juzgado/autoridad no es jurisdiccional.", "warning")
        return redirect(url_for("autoridades.detail", autoridad_id=autoridad.id))
    if autoridad.directorio_sentencias is None or autoridad.directorio_sentencias == "":
        flash("El juzgado/autoridad no tiene directorio para sentencias.", "warning")
        return redirect(url_for("autoridades.detail", autoridad_id=autoridad.id))

    # Para validar las fechas
    hoy = date.today()
    hoy_dt = datetime(year=hoy.year, month=hoy.month, day=hoy.day)
    limite_dt = hoy_dt + timedelta(days=-LIMITE_ADMINISTRADORES_DIAS)

    # Si viene el formulario
    form = SentenciaNewForm(CombinedMultiDict((request.files, request.form)))
    if form.validate_on_submit():
        es_valido = True

        # Validar sentencia
        try:
            sentencia_input = safe_sentencia(form.sentencia.data)
        except (IndexError, ValueError):
            flash("La sentencia es incorrecta.", "warning")
            es_valido = False

        # Validar sentencia_fecha
        sentencia_fecha = form.sentencia_fecha.data
        if not limite_dt <= datetime(year=sentencia_fecha.year, month=sentencia_fecha.month, day=sentencia_fecha.day) <= hoy_dt:
            flash(
                f"La fecha de la sentencia no debe ser del futuro ni anterior a {LIMITE_ADMINISTRADORES_DIAS} días.", "warning"
            )
            es_valido = False

        # Validar expediente
        try:
            expediente = safe_expediente(form.expediente.data)
        except (IndexError, ValueError):
            flash("El expediente es incorrecto.", "warning")
            es_valido = False

        # Validar fecha
        fecha = form.fecha.data
        if not limite_dt <= datetime(year=fecha.year, month=fecha.month, day=fecha.day) <= hoy_dt:
            flash(f"La fecha no debe ser del futuro ni anterior a {LIMITE_ADMINISTRADORES_DIAS} días.", "warning")
            es_valido = False

        # Tomar tipo de juicio
        materia_tipo_juicio = MateriaTipoJuicio.query.get(form.materia_tipo_juicio.data)

        # Tomar descripción
        descripcion = safe_string(form.descripcion.data, save_enie=True, max_len=1000)

        # Tomar perspectiva de género
        es_perspectiva_genero = form.es_perspectiva_genero.data  # Boleano

        # Inicializar la liberia GCS con el directorio base, la fecha, las extensiones y los meses como palabras
        gcstorage = GoogleCloudStorage(
            base_directory=autoridad.directorio_sentencias,
            upload_date=fecha,
            allowed_extensions=["pdf"],
            month_in_word=True,
            bucket_name=current_app.config["CLOUD_STORAGE_DEPOSITO_SENTENCIAS"],
        )

        # Validar archivo
        archivo = request.files["archivo"]
        try:
            gcstorage.set_content_type(archivo.filename)
        except (MyFilenameError, MyNotAllowedExtensionError, MyUnknownExtensionError):
            flash("Tipo de archivo no permitido.", "warning")
            es_valido = False
        except Exception:
            flash("Error desconocido al validar el archivo.", "danger")
            es_valido = False

        # No es válido, entonces se vuelve a mostrar el formulario
        if es_valido is False:
            return render_template("sentencias/new_for_autoridad.jinja2", form=form, autoridad=autoridad)

        # Insertar registro
        sentencia = Sentencia(
            autoridad=autoridad,
            materia_tipo_juicio=materia_tipo_juicio,
            sentencia=sentencia_input,
            sentencia_fecha=sentencia_fecha,
            expediente=expediente,
            expediente_anio=extract_expediente_anio(expediente),
            expediente_num=extract_expediente_num(expediente),
            fecha=fecha,
            descripcion=descripcion,
            es_perspectiva_genero=es_perspectiva_genero,
        )
        sentencia.save()

        # El nombre del archivo contiene FECHA/SENTENCIA/EXPEDIENTE/PERSPECTIVA_GENERO/HASH
        nombre_elementos = []
        nombre_elementos.append(sentencia_input.replace("/", "-"))
        nombre_elementos.append(expediente.replace("/", "-"))
        if es_perspectiva_genero:
            nombre_elementos.append("G")

        # Subir a Google Cloud Storage
        es_exitoso = True
        try:
            gcstorage.set_filename(hashed_id=sentencia.encode_id(), description="-".join(nombre_elementos))
            gcstorage.upload(archivo.stream.read())
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
            sentencia.archivo = gcstorage.filename  # Conservar el nombre original
            sentencia.url = gcstorage.url
            sentencia.save()
            bitacora = Bitacora(
                modulo=Modulo.query.filter_by(nombre=MODULO).first(),
                usuario=current_user,
                descripcion=safe_message(
                    f"Nueva Sentencia de {autoridad.clave} con sentencia {sentencia.sentencia} y del expediente {sentencia.expediente}"
                ),
                url=url_for("sentencias.detail", sentencia_id=sentencia.id),
            )
            bitacora.save()
            flash(bitacora.descripcion, "success")
            return redirect(bitacora.url)

        # Como no se subio con exito, se cambia el estatus a "B"
        sentencia.estatus = "B"
        sentencia.save()

    # Valores por defecto
    form.distrito.data = autoridad.distrito.nombre
    form.autoridad.data = autoridad.descripcion
    form.fecha.data = hoy

    # Entregar el formulario
    return render_template(
        "sentencias/new_for_autoridad.jinja2",
        form=form,
        autoridad=autoridad,
        materias=Materia.query.filter_by(en_sentencias=True).filter_by(estatus="A").order_by(Materia.id).all(),
        materias_tipos_juicios=MateriaTipoJuicio.query.filter_by(estatus="A")
        .order_by(MateriaTipoJuicio.materia_id, MateriaTipoJuicio.descripcion)
        .all(),
    )


@sentencias.route("/sentencias/editar/<int:sentencia_id>", methods=["GET", "POST"])
@permission_required(MODULO, Permiso.MODIFICAR)
def edit(sentencia_id):
    """Editar Sentencia"""

    # Para validar las fechas
    hoy = date.today()
    hoy_dt = datetime(year=hoy.year, month=hoy.month, day=hoy.day)
    limite_dt = hoy_dt + timedelta(days=-LIMITE_DIAS)

    # Validar sentencia
    sentencia = Sentencia.query.get_or_404(sentencia_id)
    if not (current_user.can_admin(MODULO) or current_user.autoridad_id == sentencia.autoridad_id):
        flash("No tiene permiso para editar esta sentencia.", "warning")
        return redirect(url_for("sentencias.list_active"))

    # Si viene el formulario
    form = SentenciaEditForm()
    if form.validate_on_submit():
        es_valido = True

        # Validar fecha
        fecha = form.fecha.data
        if not limite_dt <= datetime(year=fecha.year, month=fecha.month, day=fecha.day) <= hoy_dt:
            flash(f"La fecha no debe ser del futuro ni anterior a {LIMITE_DIAS} días.", "warning")
            form.fecha.data = hoy
            es_valido = False

        # Validar sentencia
        try:
            sentencia = safe_sentencia(form.sentencia.data)
        except (IndexError, ValueError):
            flash("La sentencia es incorrecta.", "warning")
            es_valido = False

        # Validar sentencia_fecha
        sentencia_fecha = form.sentencia_fecha.data
        if (
            not limite_dt
            <= datetime(
                year=sentencia.sentencia_fecha.year, month=sentencia.sentencia_fecha.month, day=sentencia.sentencia_fecha.day
            )
            <= hoy_dt
        ):
            flash(f"La fecha de la sentencia no debe ser del futuro ni anterior a {LIMITE_DIAS} días.", "warning")
            es_valido = False

        # Validar expediente
        try:
            sentencia.expediente = safe_expediente(form.expediente.data)
            sentencia.expediente_anio = extract_expediente_anio(sentencia.expediente)
            sentencia.expediente_num = extract_expediente_num(sentencia.expediente)
        except (IndexError, ValueError):
            flash("El expediente es incorrecto.", "warning")
            es_valido = False

        # Tomar perspectiva de género
        sentencia.es_perspectiva_genero = form.es_perspectiva_genero.data

        # Tomar tipo de juicio
        sentencia.materia_tipo_juicio = MateriaTipoJuicio.query.get(form.materia_tipo_juicio.data)

        # Tomar descripcion
        sentencia.descripcion = safe_string(form.descripcion.data, max_len=1000)

        # Si es válido, entonces se guarda
        if es_valido:
            sentencia.save()
            bitacora = Bitacora(
                modulo=Modulo.query.filter_by(nombre=MODULO).first(),
                usuario=current_user,
                descripcion=safe_message(
                    f"Editada la Sentencia de {sentencia.autoridad.clave} con sentencia {sentencia.sentencia} y del expediente {sentencia.expediente}"
                ),
                url=url_for("sentencias.detail", sentencia_id=sentencia.id),
            )
            bitacora.save()
            flash(bitacora.descripcion, "success")
            return redirect(bitacora.url)

    # Definir valores en el formulario
    form.sentencia.data = sentencia.sentencia
    form.sentencia_fecha.data = sentencia.sentencia_fecha
    form.expediente.data = sentencia.expediente
    form.fecha.data = sentencia.fecha
    form.descripcion.data = sentencia.descripcion
    form.es_perspectiva_genero.data = sentencia.es_perspectiva_genero

    # Entregar el formulario
    return render_template(
        "sentencias/edit.jinja2",
        form=form,
        sentencia=sentencia,
        materias=Materia.query.filter_by(en_sentencias=True).filter_by(estatus="A").order_by(Materia.id).all(),
        materias_tipos_juicios=MateriaTipoJuicio.query.filter_by(estatus="A")
        .order_by(MateriaTipoJuicio.materia_id, MateriaTipoJuicio.descripcion)
        .all(),
    )


@sentencias.route("/sentencias/eliminar/<int:sentencia_id>")
@permission_required(MODULO, Permiso.CREAR)
def delete(sentencia_id):
    """Eliminar Sentencia"""
    sentencia = Sentencia.query.get_or_404(sentencia_id)
    if sentencia.estatus == "B":
        flash("No puede eliminar esta Sentencia porque ya está eliminada.", "success")
        return redirect(url_for("sentencias.detail", sentencia_id=sentencia.id))
    if current_user.can_admin(MODULO):
        sentencia.delete()
        bitacora = Bitacora(
            modulo=Modulo.query.filter_by(nombre=MODULO).first(),
            usuario=current_user,
            descripcion=safe_message(f"Eliminada Sentencia {sentencia.id} por administrador"),
            url=url_for("sentencias.detail", sentencia_id=sentencia.id),
        )
        bitacora.save()
        flash(bitacora.descripcion, "success")
        return redirect(bitacora.url)
    if current_user.autoridad_id == sentencia.autoridad_id and sentencia.creado >= datetime.today() - timedelta(days=1):
        sentencia.delete()
        bitacora = Bitacora(
            modulo=Modulo.query.filter_by(nombre=MODULO).first(),
            usuario=current_user,
            descripcion=safe_message(f"Eliminada Sentencia {sentencia.id} por autoridad"),
            url=url_for("sentencias.detail", sentencia_id=sentencia.id),
        )
        bitacora.save()
        flash(bitacora.descripcion, "success")
        return redirect(bitacora.url)
    flash("No puede eliminar esta Sentencia porque fue creada hace más de un día.", "warning")
    return redirect(url_for("sentencias.detail", sentencia_id=sentencia.id))


@sentencias.route("/sentencias/recuperar/<int:sentencia_id>")
@permission_required(MODULO, Permiso.CREAR)
def recover(sentencia_id):
    """Recuperar Sentencia"""
    sentencia = Sentencia.query.get_or_404(sentencia_id)
    if sentencia.estatus == "A":
        flash("No puede eliminar esta Sentencia porque ya está activa.", "success")
        return redirect(url_for("sentencias.detail", sentencia_id=sentencia.id))
    if current_user.can_admin(MODULO):
        sentencia.recover()
        bitacora = Bitacora(
            modulo=Modulo.query.filter_by(nombre=MODULO).first(),
            usuario=current_user,
            descripcion=safe_message(f"Recuperada Sentencia {sentencia.id} por administrador"),
            url=url_for("sentencias.detail", sentencia_id=sentencia.id),
        )
        bitacora.save()
        flash(bitacora.descripcion, "success")
    if current_user.autoridad_id == sentencia.autoridad_id and sentencia.creado >= datetime.today() - timedelta(days=1):
        sentencia.recover()
        bitacora = Bitacora(
            modulo=Modulo.query.filter_by(nombre=MODULO).first(),
            usuario=current_user,
            descripcion=safe_message(f"Recuperada Sentencia {sentencia.id} por autoridad"),
            url=url_for("edictos.detail", glosa_id=sentencia.id),
        )
        bitacora.save()
        flash(bitacora.descripcion, "success")
        return redirect(bitacora.url)
    flash("No puede recuperar esta Sentencia porque fue creada hace más de un día.", "warning")
    return redirect(url_for("sentencias.detail", sentencia_id=sentencia.id))


@sentencias.route("/sentencias/reporte", methods=["GET", "POST"])
def report():
    """Elaborar reporte de sentencias"""
    # Preparar el formulario
    form = SentenciaReportForm()
    # Si viene el formulario
    if form.validate():
        # Tomar valores del formulario
        autoridad = Autoridad.query.get_or_404(int(form.autoridad_id.data))
        fecha_desde = form.fecha_desde.data
        fecha_hasta = form.fecha_hasta.data
        por_tipos_de_juicios = bool(form.por_tipos_de_juicios.data)
        # Si la fecha_desde es posterior a la fecha_hasta, se intercambian
        if fecha_desde > fecha_hasta:
            fecha_desde, fecha_hasta = fecha_hasta, fecha_desde
        # Si no es administrador, ni tiene un rol para elaborar reportes de todos
        if not current_user.can_admin("SENTENCIAS") and not set(current_user.get_roles()).intersection(set(ROL_REPORTES_TODOS)):
            # Si la autoridad del usuario no es la del formulario, se niega el acceso
            if current_user.autoridad_id != autoridad.id:
                flash("No tiene permiso para acceder a este reporte.", "warning")
                return redirect(url_for("sentencias.list_active"))
        # Si es por tipos de juicios
        if por_tipos_de_juicios:
            # Entregar pagina con los tipos de juicios y sus cantidades
            return render_template(
                "sentencias/report_tipos_de_juicios.jinja2",
                autoridad=autoridad,
                fecha_desde=fecha_desde,
                fecha_hasta=fecha_hasta,
                filtros=json.dumps(
                    {
                        "autoridad_id": autoridad.id,
                        "estatus": "A",
                        "fecha_desde": fecha_desde.strftime("%Y-%m-%d"),
                        "fecha_hasta": fecha_hasta.strftime("%Y-%m-%d"),
                    }
                ),
            )
        # De lo contrario, entregar pagina con el reporte de sentencias y enlaces publicos
        return render_template(
            "sentencias/report.jinja2",
            autoridad=autoridad,
            fecha_desde=fecha_desde,
            fecha_hasta=fecha_hasta,
            filtros=json.dumps(
                {
                    "autoridad_id": autoridad.id,
                    "estatus": "A",
                    "fecha_desde": fecha_desde.strftime("%Y-%m-%d"),
                    "fecha_hasta": fecha_hasta.strftime("%Y-%m-%d"),
                }
            ),
        )
    # No viene el formulario, por lo tanto se advierte del error
    flash("Error: datos incorrectos para hacer el reporte de sentencias.", "warning")
    return redirect(url_for("sentencias.list_active"))


@sentencias.route("/sentencias/ver_archivo_pdf/<int:sentencia_id>")
def view_file_pdf(sentencia_id):
    """Ver archivo PDF de Edicto para insertarlo en un iframe en el detalle"""

    # Consultar
    sentencia = Sentencia.query.get_or_404(sentencia_id)

    # Obtener el contenido del archivo
    try:
        archivo = get_file_from_gcs(
            bucket_name=current_app.config["CLOUD_STORAGE_DEPOSITO_EDICTOS"],
            blob_name=get_blob_name_from_url(sentencia.url),
        )
    except (MyBucketNotFoundError, MyFileNotFoundError, MyNotValidParamError) as error:
        raise NotFound("No se encontró el archivo.") from error

    # Entregar el archivo
    response = make_response(archivo)
    response.headers["Content-Type"] = "application/pdf"
    return response


@sentencias.route("/sentencias/descargar_archivo_pdf/<int:sentencia_id>")
def download_file_pdf(sentencia_id):
    """Descargar archivo PDF de Edicto"""

    # Consultar
    sentencia = Sentencia.query.get_or_404(sentencia_id)

    # Obtener el contenido del archivo
    try:
        archivo = get_file_from_gcs(
            bucket_name=current_app.config["CLOUD_STORAGE_DEPOSITO_EDICTOS"],
            blob_name=get_blob_name_from_url(sentencia.url),
        )
    except (MyBucketNotFoundError, MyFileNotFoundError, MyNotValidParamError) as error:
        raise NotFound("No se encontró el archivo.")

    # Entregar el archivo
    response = make_response(archivo)
    response.headers["Content-Type"] = "application/pdf"
    response.headers["Content-Disposition"] = f"attachment; filename={sentencia.archivo}"
    return response
