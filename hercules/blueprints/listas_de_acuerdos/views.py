"""
Listas de acuerdos, vistas
"""

from datetime import datetime, date, time, timedelta
import json
import re

from flask import Blueprint, current_app, flash, make_response, redirect, render_template, request, url_for
from flask_login import current_user, login_required
from pytz import timezone
from werkzeug.datastructures import CombinedMultiDict

from hercules.blueprints.autoridades.models import Autoridad
from hercules.blueprints.bitacoras.models import Bitacora
from hercules.blueprints.modulos.models import Modulo
from hercules.blueprints.listas_de_acuerdos.forms import ListaDeAcuerdoNewForm, ListaDeAcuerdoMateriaNewForm
from hercules.blueprints.listas_de_acuerdos.models import ListaDeAcuerdo
from hercules.blueprints.permisos.models import Permiso
from hercules.blueprints.usuarios.decorators import permission_required
from lib.datatables import get_datatable_parameters, output_datatable_json
from lib.exceptions import (
    MyBucketNotFoundError,
    MyFilenameError,
    MyFileNotFoundError,
    MyNotAllowedExtensionError,
    MyUnknownExtensionError,
    MyNotValidParamError,
)
from lib.google_cloud_storage import get_blob_name_from_url, get_file_from_gcs
from lib.safe_string import safe_message, safe_string, safe_clave
from lib.storage import GoogleCloudStorage

LIMITE_DIAS = 365  # Un anio, aunque autoridad.limite_dias_listas_de_acuerdos sea mayor, gana el menor
LIMITE_ADMINISTRADORES_DIAS = 3650  # Administradores pueden manipular diez anios
ORGANOS_JURISDICCIONALES_QUE_PUEDEN_ELEGIR_MATERIA = (
    "JUZGADO DE PRIMERA INSTANCIA ORAL",
    "PLENO O SALA DEL TSJ",
    "TRIBUNAL DISTRITAL",
)
HORAS_BUENO = 14
HORAS_CRITICO = 16

TIMEZONE = "America/Mexico_City"
local_tz = timezone(TIMEZONE)
medianoche = time.min

MODULO = "LISTAS DE ACUERDOS"

listas_de_acuerdos = Blueprint("listas_de_acuerdos", __name__, template_folder="templates")


@listas_de_acuerdos.before_request
@login_required
@permission_required(MODULO, Permiso.VER)
def before_request():
    """Permiso por defecto"""


@listas_de_acuerdos.route("/listas_de_acuerdos/datatable_json", methods=["GET", "POST"])
def datatable_json():
    """DataTable JSON para listado de ListaDeAcuerdo"""
    # Tomar parámetros de Datatables
    draw, start, rows_per_page = get_datatable_parameters()
    # Consultar
    consulta = ListaDeAcuerdo.query
    # Primero filtrar por columnas propias
    if "estatus" in request.form:
        consulta = consulta.filter_by(estatus=request.form["estatus"])
    else:
        consulta = consulta.filter_by(estatus="A")
    if "autoridad_id" in request.form:
        consulta = consulta.filter_by(autoridad_id=request.form["autoridad_id"])
    fecha_desde = None
    fecha_hasta = None
    if "fecha_desde" in request.form and re.match(r"\d{4}-\d{2}-\d{2}", request.form["fecha_desde"]):
        fecha_desde = request.form["fecha_desde"]
    if "fecha_hasta" in request.form and re.match(r"\d{4}-\d{2}-\d{2}", request.form["fecha_hasta"]):
        fecha_hasta = request.form["fecha_hasta"]
    if fecha_desde and fecha_hasta and fecha_desde > fecha_hasta:
        fecha_desde, fecha_hasta = fecha_hasta, fecha_desde
    if fecha_desde:
        consulta = consulta.filter(ListaDeAcuerdo.fecha >= fecha_desde)
    if fecha_hasta:
        consulta = consulta.filter(ListaDeAcuerdo.fecha <= fecha_hasta)
    # Ordenar y paginar
    registros = consulta.order_by(ListaDeAcuerdo.fecha.desc()).offset(start).limit(rows_per_page).all()
    total = consulta.count()
    # Elaborar datos para DataTable
    data = []
    for lista_de_acuerdo in registros:
        # La columna creado esta en UTC, convertir a local
        creado_local = lista_de_acuerdo.creado.astimezone(local_tz)
        # Determinar el tiempo bueno
        tiempo_limite_bueno = datetime.combine(lista_de_acuerdo.fecha, medianoche) + timedelta(hours=HORAS_BUENO)
        # Determinar el fiempo critico
        tiempo_limite_critico = datetime.combine(lista_de_acuerdo.fecha, medianoche) + timedelta(hours=HORAS_CRITICO)
        # Por defecto el semaforo es verde (0)
        semaforo = 0
        # Si creado_local es mayor a tiempo_limite_bueno, entonces el semaforo es amarillo (1)
        if creado_local > local_tz.localize(tiempo_limite_bueno):
            semaforo = 1
        # Si creado_local es mayor a tiempo_limite_critico, entonces el semaforo es rojo (2)
        if creado_local > local_tz.localize(tiempo_limite_critico):
            semaforo = 2
        # Acumular datos
        data.append(
            {
                "detalle": {
                    "fecha": lista_de_acuerdo.fecha.strftime("%Y-%m-%d"),
                    "url": url_for("listas_de_acuerdos.detail", lista_de_acuerdo_id=lista_de_acuerdo.id),
                },
                "descripcion": lista_de_acuerdo.descripcion,
                "creado": {
                    "tiempo": creado_local.strftime("%Y-%m-%d %H:%M"),
                    "semaforo": semaforo,
                },
            }
        )
    # Entregar JSON
    return output_datatable_json(draw, total, data)


@listas_de_acuerdos.route("/listas_de_acuerdos/admin_datatable_json", methods=["GET", "POST"])
def admin_datatable_json():
    """DataTable JSON para listado admin de ListaDeAcuerdo"""
    # Tomar parámetros de Datatables
    draw, start, rows_per_page = get_datatable_parameters()
    # Consultar
    consulta = ListaDeAcuerdo.query
    # Primero filtrar por columnas propias
    if "estatus" in request.form:
        consulta = consulta.filter(ListaDeAcuerdo.estatus == request.form["estatus"])
    else:
        consulta = consulta.filter(ListaDeAcuerdo.estatus == "A")
    if "autoridad_id" in request.form:
        consulta = consulta.filter(ListaDeAcuerdo.autoridad_id == request.form["autoridad_id"])
    elif "autoridad_clave" in request.form:
        clave = safe_clave(request.form["autoridad_clave"])
        if clave != "":
            consulta = consulta.join(ListaDeAcuerdo.autoridad).filter(Autoridad.clave.contains(clave))
    fecha_desde = None
    fecha_hasta = None
    if "fecha_desde" in request.form and re.match(r"\d{4}-\d{2}-\d{2}", request.form["fecha_desde"]):
        fecha_desde = request.form["fecha_desde"]
    if "fecha_hasta" in request.form and re.match(r"\d{4}-\d{2}-\d{2}", request.form["fecha_hasta"]):
        fecha_hasta = request.form["fecha_hasta"]
    if fecha_desde and fecha_hasta and fecha_desde > fecha_hasta:
        fecha_desde, fecha_hasta = fecha_hasta, fecha_desde
    if fecha_desde:
        consulta = consulta.filter(ListaDeAcuerdo.fecha >= fecha_desde)
    if fecha_hasta:
        consulta = consulta.filter(ListaDeAcuerdo.fecha <= fecha_hasta)
    # Ordenar y paginar
    registros = consulta.order_by(ListaDeAcuerdo.id.desc()).offset(start).limit(rows_per_page).all()
    total = consulta.count()
    # Elaborar datos para DataTable
    data = []
    for lista_de_acuerdo in registros:
        # La columna creado esta en UTC, convertir a local
        creado_local = lista_de_acuerdo.creado.astimezone(local_tz)
        # Determinar el tiempo bueno
        tiempo_limite_bueno = datetime.combine(lista_de_acuerdo.fecha, medianoche) + timedelta(hours=HORAS_BUENO)
        # Determinar el fiempo critico
        tiempo_limite_critico = datetime.combine(lista_de_acuerdo.fecha, medianoche) + timedelta(hours=HORAS_CRITICO)
        # Por defecto el semaforo es verde (0)
        semaforo = 0
        # Si la autoridad tiene limite_dias_listas_de_acuerdos igual a cero
        if lista_de_acuerdo.autoridad.limite_dias_listas_de_acuerdos == 0:
            # Si creado_local es mayor a tiempo_limite_bueno, entonces el semaforo es amarillo (1)
            if creado_local > local_tz.localize(tiempo_limite_bueno):
                semaforo = 1
            # Si creado_local es mayor a tiempo_limite_critico, entonces el semaforo es rojo (2)
            if creado_local > local_tz.localize(tiempo_limite_critico):
                semaforo = 2
        # Acumular datos
        data.append(
            {
                "detalle": {
                    "id": lista_de_acuerdo.id,
                    "url": url_for("listas_de_acuerdos.detail", lista_de_acuerdo_id=lista_de_acuerdo.id),
                },
                "creado": {
                    "tiempo": creado_local.strftime("%Y-%m-%d %H:%M"),
                    "semaforo": semaforo,
                },
                "autoridad_clave": lista_de_acuerdo.autoridad.clave,
                "fecha": lista_de_acuerdo.fecha.strftime("%Y-%m-%d"),
                "descripcion": lista_de_acuerdo.descripcion,
            }
        )
    # Entregar JSON
    return output_datatable_json(draw, total, data)


@listas_de_acuerdos.route("/listas_de_acuerdos")
def list_active():
    """Listado de ListaDeAcuerdo activos"""
    # Si es administrador ve todas las listas de acuerdos
    if current_user.can_admin("LISTAS DE ACUERDOS"):
        return render_template(
            "listas_de_acuerdos/list_admin.jinja2",
            filtros=json.dumps({"estatus": "A"}),
            titulo="Todas las listas de Acuerdos",
            estatus="A",
        )
    # Si es jurisdiccional ve lo de su autoridad
    if current_user.autoridad.es_jurisdiccional:
        autoridad = current_user.autoridad
        return render_template(
            "listas_de_acuerdos/list.jinja2",
            autoridad=autoridad,
            filtros=json.dumps({"autoridad_id": autoridad.id, "estatus": "A"}),
            titulo=f"Listas de Acuerdos de {autoridad.descripcion_corta}",
            estatus="A",
        )
    # Ninguno de los anteriores, es solo observador
    return render_template(
        "listas_de_acuerdos/list.jinja2",
        filtros=json.dumps({"estatus": "A"}),
        titulo="Listas de Acuerdos (observador)",
        estatus="A",
    )


@listas_de_acuerdos.route("/listas_de_acuerdos/inactivos")
@permission_required(MODULO, Permiso.ADMINISTRAR)
def list_inactive():
    """Listado de ListaDeAcuerdo inactivas"""
    # Solo los administradores ven todas las listas de acuerdos inactivas
    return render_template(
        "listas_de_acuerdos/list_admin.jinja2",
        filtros=json.dumps({"estatus": "B"}),
        titulo="Todas las listas de Acuerdos inactivas",
        estatus="B",
    )


@listas_de_acuerdos.route("/listas_de_acuerdos/<int:lista_de_acuerdo_id>")
def detail(lista_de_acuerdo_id):
    """Detalle de una ListaDeAcuerdo"""
    lista_de_acuerdo = ListaDeAcuerdo.query.get_or_404(lista_de_acuerdo_id)
    return render_template("listas_de_acuerdos/detail.jinja2", lista_de_acuerdo=lista_de_acuerdo)


@listas_de_acuerdos.route("/listas_de_acuerdos/nuevo", methods=["GET", "POST"])
@permission_required(MODULO, Permiso.CREAR)
def new():
    """Subir ListaDeAcuerdo como Juzgado"""

    # Validar autoridad
    autoridad = current_user.autoridad
    if autoridad is None or autoridad.estatus != "A":
        flash("El juzgado/autoridad no existe o no es activa.", "warning")
        return redirect(url_for("listas_de_acuerdos.list_active"))
    if not autoridad.distrito.es_distrito_judicial:
        flash("El juzgado/autoridad no está en un distrito jurisdiccional.", "warning")
        return redirect(url_for("listas_de_acuerdos.list_active"))
    if not autoridad.es_jurisdiccional:
        flash("El juzgado/autoridad no es jurisdiccional.", "warning")
        return redirect(url_for("listas_de_acuerdos.list_active"))
    if autoridad.directorio_listas_de_acuerdos is None or autoridad.directorio_listas_de_acuerdos == "":
        flash("El juzgado/autoridad no tiene directorio para listas de acuerdos.", "warning")
        return redirect(url_for("listas_de_acuerdos.list_active"))

    # Google App Engine usa tiempo universal, sin esta correccion las fechas de la noche cambian al dia siguiente
    ahora_utc = datetime.now(timezone("UTC"))
    ahora_mx_coah = ahora_utc.astimezone(local_tz)

    # Para validar la fecha
    hoy = ahora_mx_coah.date()
    hoy_dt = ahora_mx_coah
    if autoridad.limite_dias_listas_de_acuerdos < LIMITE_DIAS:
        mi_limite_dias = autoridad.limite_dias_listas_de_acuerdos
    else:
        mi_limite_dias = LIMITE_DIAS
    if mi_limite_dias > 0:
        limite_dt = hoy_dt + timedelta(days=-mi_limite_dias)
    else:
        limite_dt = hoy_dt

    # Decidir entre formulario sin materia o con materia
    con_materia = autoridad.organo_jurisdiccional in ORGANOS_JURISDICCIONALES_QUE_PUEDEN_ELEGIR_MATERIA
    if con_materia:
        form = ListaDeAcuerdoMateriaNewForm(CombinedMultiDict((request.files, request.form)))
    else:
        form = ListaDeAcuerdoNewForm(CombinedMultiDict((request.files, request.form)))

    # Si viene el formulario
    if form.validate_on_submit():
        es_valido = True

        # Validar fecha
        if mi_limite_dias > 0:
            fecha = form.fecha.data
            if not limite_dt <= datetime(year=fecha.year, month=fecha.month, day=fecha.day, tzinfo=local_tz) <= hoy_dt:
                flash(f"La fecha no debe ser del futuro ni anterior a {mi_limite_dias} días.", "warning")
                es_valido = False
        else:
            fecha = hoy

        # Inicializar la liberia GCS con el directorio base, la fecha, las extensiones permitidas y los meses como palabras
        gcstorage = GoogleCloudStorage(
            base_directory=autoridad.directorio_listas_de_acuerdos,
            upload_date=fecha,
            allowed_extensions=["pdf"],
            month_in_word=True,
            bucket_name=current_app.config["CLOUD_STORAGE_DEPOSITO_LISTAS_DE_ACUERDOS"],
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
            return render_template(
                "listas_de_acuerdos/new.jinja2",
                form=form,
                mi_limite_dias=mi_limite_dias,
                con_materia=con_materia,
            )

        # Definir descripcion
        descripcion = "LISTA DE ACUERDOS"
        if con_materia:
            materia = form.materia.data
            if materia.id != 1:  # NO DEFINIDO
                descripcion = safe_string(f"LISTA DE ACUERDOS {materia.nombre}")

        # Si existe una lista de acuerdos de la misma fecha, dar de baja la antigua
        anterior_borrada = False
        if con_materia is False:
            anterior_lista_de_acuerdo = (
                ListaDeAcuerdo.query.filter(ListaDeAcuerdo.autoridad == autoridad)
                .filter(ListaDeAcuerdo.fecha == fecha)
                .filter_by(estatus="A")
                .first()
            )
            if anterior_lista_de_acuerdo:
                anterior_lista_de_acuerdo.delete()
                anterior_borrada = True
        else:
            anterior_lista_de_acuerdo = (
                ListaDeAcuerdo.query.filter(ListaDeAcuerdo.autoridad == autoridad)
                .filter(ListaDeAcuerdo.fecha == fecha)
                .filter_by(descripcion=descripcion)
                .filter_by(estatus="A")
                .first()
            )
            if anterior_lista_de_acuerdo:
                anterior_lista_de_acuerdo.delete()
                anterior_borrada = True

        # Insertar registro
        lista_de_acuerdo = ListaDeAcuerdo(
            autoridad=autoridad,
            fecha=fecha,
            descripcion=descripcion,
        )
        lista_de_acuerdo.save()

        # Subir a Google Cloud Storage
        es_exitoso = True
        try:
            gcstorage.set_filename(hashed_id=lista_de_acuerdo.encode_id(), description=descripcion)
            gcstorage.upload(archivo.stream.read())
        except (MyFilenameError, MyNotAllowedExtensionError, MyUnknownExtensionError):
            flash("Tipo de archivo no permitido.", "warning")
            es_exitoso = False
        except Exception:
            flash("Error desconocido al subir el archivo.", "danger")
            es_exitoso = False

        # Si se sube con exito, actualizar el registro con la URL del archivo y mostrar el detalle
        if es_exitoso:
            lista_de_acuerdo.archivo = gcstorage.filename
            lista_de_acuerdo.url = gcstorage.url
            lista_de_acuerdo.save()
            if anterior_borrada:
                bitacora_descripcion = "Reemplazada "
            else:
                bitacora_descripcion = "Nueva "
            bitacora_descripcion += f"lista de acuerdos del {lista_de_acuerdo.fecha.strftime('%Y-%m-%d')} de {autoridad.clave}"
            bitacora = Bitacora(
                modulo=Modulo.query.filter_by(nombre=MODULO).first(),
                usuario=current_user,
                descripcion=safe_message(bitacora_descripcion),
                url=url_for("listas_de_acuerdos.detail", lista_de_acuerdo_id=lista_de_acuerdo.id),
            )
            bitacora.save()
            flash(bitacora.descripcion, "success")
            return redirect(bitacora.url)

    # Llenar de los campos del formulario
    form.distrito.data = autoridad.distrito.nombre
    form.autoridad.data = autoridad.descripcion
    form.fecha.data = hoy

    # Si puede elegir la materia
    if con_materia:
        form.materia.data = Materia.query.get(1)  # Por defecto NO DEFINIDO

    # Mostrar formulario
    return render_template(
        "listas_de_acuerdos/new.jinja2",
        form=form,
        mi_limite_dias=mi_limite_dias,
        con_materia=con_materia,
    )


@listas_de_acuerdos.route("/listas_de_acuerdos/eliminar/<int:lista_de_acuerdo_id>")
@permission_required(MODULO, Permiso.CREAR)
def delete(lista_de_acuerdo_id):
    """Eliminar ListaDeAcuerdo"""
    lista_de_acuerdo = ListaDeAcuerdo.query.get_or_404(lista_de_acuerdo_id)
    bitacora_descripcion = f"Eliminada la lista de acuerdos del {lista_de_acuerdo.fecha.strftime('%Y-%m-%d')} de {lista_de_acuerdo.autoridad.clave}"
    if lista_de_acuerdo.estatus == "A":
        # Los administradores puede eliminar cualquiera dentro de los limites
        if current_user.can_admin("LISTAS DE ACUERDOS"):
            hoy = date.today()
            hoy_dt = datetime(year=hoy.year, month=hoy.month, day=hoy.day)
            limite_dt = hoy_dt + timedelta(days=-LIMITE_ADMINISTRADORES_DIAS)
            if limite_dt.timestamp() > lista_de_acuerdo.creado.timestamp():
                flash("No puede eliminar porque fue creado antes de la fecha límite.", "warning")
                return redirect(url_for("listas_de_acuerdos.detail", lista_de_acuerdo_id=lista_de_acuerdo.id))
            lista_de_acuerdo.delete()
            bitacora = Bitacora(
                modulo=Modulo.query.filter_by(nombre=MODULO).first(),
                usuario=current_user,
                descripcion=safe_message(bitacora_descripcion),
                url=url_for("listas_de_acuerdos.detail", lista_de_acuerdo_id=lista_de_acuerdo.id),
            )
            bitacora.save()
            flash(bitacora.descripcion, "success")
        # Los jurisdiccionales solo pueden eliminar las suyas y que sean de hoy
        elif current_user.autoridad_id == lista_de_acuerdo.autoridad_id and lista_de_acuerdo.fecha == date.today():
            lista_de_acuerdo.delete()
            bitacora = Bitacora(
                modulo=Modulo.query.filter_by(nombre=MODULO).first(),
                usuario=current_user,
                descripcion=safe_message(bitacora_descripcion),
                url=url_for("listas_de_acuerdos.detail", lista_de_acuerdo_id=lista_de_acuerdo.id),
            )
            bitacora.save()
            flash(bitacora.descripcion, "success")
        else:
            flash("No tiene permiso para eliminar o sólo puede eliminar de hoy.", "warning")
    return redirect(url_for("listas_de_acuerdos.detail", lista_de_acuerdo_id=lista_de_acuerdo.id))


@listas_de_acuerdos.route("/listas_de_acuerdos/recuperar/<int:lista_de_acuerdo_id>")
@permission_required(MODULO, Permiso.CREAR)
def recover(lista_de_acuerdo_id):
    """Recuperar ListaDeAcuerdo"""
    lista_de_acuerdo = ListaDeAcuerdo.query.get_or_404(lista_de_acuerdo_id)
    bitacora_descripcion = f"Recuperada la lista de acuerdos del {lista_de_acuerdo.fecha.strftime('%Y-%m-%d')} de {lista_de_acuerdo.autoridad.clave}"
    if lista_de_acuerdo.estatus == "B":
        # Evitar que se recupere si ya existe una con la misma fecha
        if (
            ListaDeAcuerdo.query.filter(ListaDeAcuerdo.autoridad == current_user.autoridad)
            .filter(ListaDeAcuerdo.fecha == lista_de_acuerdo.fecha)
            .filter_by(estatus="A")
            .first()
        ):
            flash("No puede recuperar esta lista porque ya hay una activa de la misma fecha.", "warning")
            return redirect(url_for("listas_de_acuerdos.detail", lista_de_acuerdo_id=lista_de_acuerdo.id))
        # Los administradores pueden recuperar cualquiera dentro de los limites
        if current_user.can_admin("LISTAS DE ACUERDOS"):
            hoy = date.today()
            hoy_dt = datetime(year=hoy.year, month=hoy.month, day=hoy.day)
            limite_dt = hoy_dt + timedelta(days=-LIMITE_ADMINISTRADORES_DIAS)
            if limite_dt.timestamp() > lista_de_acuerdo.creado.timestamp():
                flash("No puede recuperar porque fue creado antes de la fecha límite.", "warning")
                return redirect(url_for("listas_de_acuerdos.detail", lista_de_acuerdo_id=lista_de_acuerdo.id))
            lista_de_acuerdo.recover()
            bitacora = Bitacora(
                modulo=Modulo.query.filter_by(nombre=MODULO).first(),
                usuario=current_user,
                descripcion=safe_message(bitacora_descripcion),
                url=url_for("listas_de_acuerdos.detail", lista_de_acuerdo_id=lista_de_acuerdo.id),
            )
            bitacora.save()
            flash(bitacora.descripcion, "success")
        elif current_user.autoridad_id == lista_de_acuerdo.autoridad_id and lista_de_acuerdo.fecha == date.today():
            lista_de_acuerdo.recover()
            bitacora = Bitacora(
                modulo=Modulo.query.filter_by(nombre=MODULO).first(),
                usuario=current_user,
                descripcion=safe_message(bitacora_descripcion),
                url=url_for("listas_de_acuerdos.detail", lista_de_acuerdo_id=lista_de_acuerdo.id),
            )
            bitacora.save()
            flash(bitacora.descripcion, "success")
        else:
            flash("No tiene permiso para recuperar o sólo puede recuperar de hoy.", "warning")
    return redirect(url_for("listas_de_acuerdos.detail", lista_de_acuerdo_id=lista_de_acuerdo.id))


@listas_de_acuerdos.route("/listas_de_acuerdos/ver_archivo_pdf/<int:lista_de_acuerdo_id>")
def view_file_pdf(lista_de_acuerdo_id):
    """Ver archivo PDF de ListaDeAcuerdo para insertarlo en un iframe en el detalle"""

    # Consultar la lista de acuerdos
    lista_de_acuerdo = ListaDeAcuerdo.query.get_or_404(lista_de_acuerdo_id)

    # Obtener el contenido del archivo
    archivo = None
    try:
        archivo = get_file_from_gcs(
            bucket_name=current_app.config["CLOUD_STORAGE_DEPOSITO_LISTAS_DE_ACUERDOS"],
            blob_name=get_blob_name_from_url(lista_de_acuerdo.url),
        )
    except (MyBucketNotFoundError, MyFileNotFoundError, MyNotValidParamError) as error:
        pass

    # Si no se obtiene el archivo, no se entrega nada
    if archivo is None:
        flash("No se encontró el archivo.", "warning")
        return ""

    # Entregar el archivo
    response = make_response(archivo)
    response.headers["Content-Type"] = "application/pdf"
    return response
