"""
Inventarios Equipos Fotos, vistas
"""

import json

from flask import Blueprint, flash, redirect, render_template, request, url_for
from flask_login import current_user, login_required
from werkzeug.datastructures import CombinedMultiDict

from hercules.blueprints.bitacoras.models import Bitacora
from hercules.blueprints.inv_equipos.models import InvEquipo
from hercules.blueprints.inv_equipos_fotos.forms import InvEquipoFotoForm
from hercules.blueprints.inv_equipos_fotos.models import InvEquipoFoto
from hercules.blueprints.modulos.models import Modulo
from hercules.blueprints.permisos.models import Permiso
from hercules.blueprints.usuarios.decorators import permission_required
from lib.datatables import get_datatable_parameters, output_datatable_json
from lib.exceptions import MyFilenameError, MyNotAllowedExtensionError, MyUnknownExtensionError
from lib.safe_string import safe_message, safe_string
from lib.storage import GoogleCloudStorage

MODULO = "INV EQUIPOS FOTOS"
SUBDIRECTORIO = "inv_equipos_fotos"

inv_equipos_fotos = Blueprint("inv_equipos_fotos", __name__, template_folder="templates")


@inv_equipos_fotos.before_request
@login_required
@permission_required(MODULO, Permiso.VER)
def before_request():
    """Permiso por defecto"""


@inv_equipos_fotos.route("/inv_equipos_fotos/datatable_json", methods=["GET", "POST"])
def datatable_json():
    """DataTable JSON para listado de InvEquipoFoto"""
    # Tomar parámetros de Datatables
    draw, start, rows_per_page = get_datatable_parameters()
    # Consultar
    consulta = InvEquipoFoto.query
    # Primero filtrar por columnas propias
    if "estatus" in request.form:
        consulta = consulta.filter_by(estatus=request.form["estatus"])
    else:
        consulta = consulta.filter_by(estatus="A")
    if "inv_equipo_id" in request.form:
        consulta = consulta.filter_by(inv_equipo_id=request.form["inv_equipo_id"])
    if "descripcion" in request.form:
        descripcion = safe_string(request.form["descripcion"])
        if descripcion != "":
            consulta = consulta.filter(InvEquipoFoto.descripcion.contains(descripcion))
    # Ordenar y paginar
    registros = consulta.order_by(InvEquipoFoto.id).offset(start).limit(rows_per_page).all()
    total = consulta.count()
    # Elaborar datos para DataTable
    data = []
    for resultado in registros:
        data.append(
            {
                "detalle": {
                    "archivo": resultado.archivo,
                    "url": url_for("inv_equipos_fotos.detail", inv_equipo_foto_id=resultado.id),
                },
                "descripcion": resultado.descripcion,
            }
        )
    # Entregar JSON
    return output_datatable_json(draw, total, data)


@inv_equipos_fotos.route("/inv_equipos_fotos")
def list_active():
    """Listado de InvEquipoFoto activas"""
    return render_template(
        "inv_equipos_fotos/list.jinja2",
        filtros=json.dumps({"estatus": "A"}),
        titulo="Fotos de Equipos",
        estatus="A",
    )


@inv_equipos_fotos.route("/inv_equipos_fotos/inactivos")
@permission_required(MODULO, Permiso.ADMINISTRAR)
def list_inactive():
    """Listado de InvEquipoFoto inactivas"""
    return render_template(
        "inv_equipos_fotos/list.jinja2",
        filtros=json.dumps({"estatus": "B"}),
        titulo="Fotos de Equipos inactivas",
        estatus="B",
    )


@inv_equipos_fotos.route("/inv_equipos_fotos/<int:inv_equipo_foto_id>")
def detail(inv_equipo_foto_id):
    """Detalle de una InvEquipoFoto"""
    inv_equipo_foto = InvEquipoFoto.query.get_or_404(inv_equipo_foto_id)
    return render_template("inv_equipos_fotos/detail.jinja2", inv_equipo_foto=inv_equipo_foto)


@inv_equipos_fotos.route("/inv_equipos_fotos/nuevo/<int:inv_equipo_id>", methods=["GET", "POST"])
@permission_required(MODULO, Permiso.CREAR)
def new_with_inv_equipo_id(inv_equipo_id):
    """Adjuntar una fotografia al InvEquipo dado"""
    # Validar el InvEquipo
    inv_equipo = InvEquipo.query.get_or_404(inv_equipo_id)
    if inv_equipo.estatus != "A":
        flash("El equipo no está activo", "danger")
        return redirect(url_for("inv_equipos.detail", inv_equipo_id=inv_equipo_id))
    form = InvEquipoFotoForm(CombinedMultiDict((request.files, request.form)))
    if form.validate_on_submit():
        es_valido = True
        # Validar la descripcion
        descripcion = safe_string(form.descripcion.data, save_enie=True)
        if descripcion == "":
            flash("La descripción no puede estar vacía", "danger")
            es_valido = False
        # Validar el archivo
        archivo = request.files["archivo"]
        storage = GoogleCloudStorage(base_directory=SUBDIRECTORIO, allowed_extensions=["jpg", "jpeg", "png"])
        try:
            storage.set_content_type(archivo.filename)
        except MyNotAllowedExtensionError:
            flash("Tipo de archivo no permitido.", "warning")
            es_valido = False
        except MyUnknownExtensionError:
            flash("Tipo de archivo desconocido.", "warning")
            es_valido = False
        # Si es válido
        if es_valido:
            # Insertar el registro, para obtener el ID
            inv_equipo_foto = InvEquipoFoto(
                inv_equipo=inv_equipo,
                descripcion=safe_string(descripcion),
            )
            inv_equipo_foto.save()
            # Subir el archivo a la nube
            try:
                storage.set_filename(hashed_id=inv_equipo_foto.encode_id(), description=descripcion)
                storage.upload(archivo.stream.read())
                inv_equipo_foto.archivo = archivo.filename  # Conservar el nombre original
                inv_equipo_foto.url = storage.url
                inv_equipo_foto.save()
            except (MyFilenameError, MyNotAllowedExtensionError, MyUnknownExtensionError):
                flash("Error fatal al subir el archivo a GCS.", "danger")
            except Exception as err:
                flash("Error desconocido al subir el archivo a GCS.", "danger")
            # Guardar bitácora
            bitacora = Bitacora(
                modulo=Modulo.query.filter_by(nombre=MODULO).first(),
                usuario=current_user,
                descripcion=safe_message(f"Nueva InvEquipoFoto {inv_equipo_foto.archivo} del InvEquipo {inv_equipo.id}"),
                url=url_for("inv_equipos.detail", inv_equipo_id=inv_equipo.id),
            )
            bitacora.save()
            # Redireccionar al detalle de InvEquipo
            flash("Foto guardada", "success")
            return redirect(url_for("inv_equipos.detail", inv_equipo_id=inv_equipo.id))
    # Entregar formulario
    return render_template("inv_equipos_fotos/new.jinja2", form=form, inv_equipo=inv_equipo)


@inv_equipos_fotos.route("/inv_equipos_fotos/eliminar/<int:inv_equipo_foto_id>")
@permission_required(MODULO, Permiso.ADMINISTRAR)
def delete(inv_equipo_foto_id):
    """Eliminar InvEquipoFoto"""
    inv_equipo_foto = InvEquipoFoto.query.get_or_404(inv_equipo_foto_id)
    if inv_equipo_foto.estatus == "A":
        inv_equipo_foto.delete()
        bitacora = Bitacora(
            modulo=Modulo.query.filter_by(nombre=MODULO).first(),
            usuario=current_user,
            descripcion=safe_message(f"Eliminado InvEquipoFoto {inv_equipo_foto.id}"),
            url=url_for("inv_equipos_fotos.detail", inv_equipo_foto_id=inv_equipo_foto.id),
        )
        bitacora.save()
        flash(bitacora.descripcion, "success")
    return redirect(url_for("inv_equipos_fotos.detail", inv_equipo_foto_id=inv_equipo_foto.id))


@inv_equipos_fotos.route("/inv_equipos_fotos/recuperar/<int:inv_equipo_foto_id>")
@permission_required(MODULO, Permiso.ADMINISTRAR)
def recover(inv_equipo_foto_id):
    """Recuperar InvEquipoFoto"""
    inv_equipo_foto = InvEquipoFoto.query.get_or_404(inv_equipo_foto_id)
    if inv_equipo_foto.estatus == "B":
        inv_equipo_foto.recover()
        bitacora = Bitacora(
            modulo=Modulo.query.filter_by(nombre=MODULO).first(),
            usuario=current_user,
            descripcion=safe_message(f"Recuperado InvEquipoFoto {inv_equipo_foto.id}"),
            url=url_for("inv_equipos_fotos.detail", inv_equipo_foto_id=inv_equipo_foto.id),
        )
        bitacora.save()
        flash(bitacora.descripcion, "success")
    return redirect(url_for("inv_equipos_fotos.detail", inv_equipo_foto_id=inv_equipo_foto.id))
