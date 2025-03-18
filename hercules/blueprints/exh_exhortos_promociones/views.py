"""
Exh Exhortos Promociones, vistas
"""

import json
from datetime import datetime

from flask import Blueprint, flash, redirect, render_template, request, url_for
from flask_login import current_user, login_required

from hercules.blueprints.bitacoras.models import Bitacora
from hercules.blueprints.exh_exhortos.models import ExhExhorto
from hercules.blueprints.exh_exhortos_promociones.forms import ExhExhortoPromocionForm
from hercules.blueprints.exh_exhortos_promociones.models import ExhExhortoPromocion
from hercules.blueprints.modulos.models import Modulo
from hercules.blueprints.municipios.models import Municipio
from hercules.blueprints.permisos.models import Permiso
from hercules.blueprints.usuarios.decorators import permission_required
from lib.datatables import get_datatable_parameters, output_datatable_json
from lib.pwgen import generar_identificador
from lib.safe_string import safe_message, safe_string

MODULO = "EXH EXHORTOS PROMOCIONES"

exh_exhortos_promociones = Blueprint("exh_exhortos_promociones", __name__, template_folder="templates")


@exh_exhortos_promociones.before_request
@login_required
@permission_required(MODULO, Permiso.VER)
def before_request():
    """Permiso por defecto"""


@exh_exhortos_promociones.route("/exh_exhortos_promociones/datatable_json", methods=["GET", "POST"])
def datatable_json():
    """DataTable JSON para listado de promociones"""
    # Tomar parámetros de Datatables
    draw, start, rows_per_page = get_datatable_parameters()
    # Consultar
    consulta = ExhExhortoPromocion.query
    # Primero filtrar por columnas propias
    if "estatus" in request.form:
        consulta = consulta.filter_by(estatus=request.form["estatus"])
    else:
        consulta = consulta.filter_by(estatus="A")
    if "exh_exhorto_id" in request.form:
        consulta = consulta.filter_by(exh_exhorto_id=request.form["exh_exhorto_id"])
    # Ordenar y paginar
    registros = consulta.order_by(ExhExhortoPromocion.id.desc()).offset(start).limit(rows_per_page).all()
    total = consulta.count()
    # Elaborar datos para DataTable
    data = []
    for resultado in registros:
        data.append(
            {
                "detalle": {
                    "folio_origen_promocion": resultado.folio_origen_promocion,
                    "url": url_for("exh_exhortos_promociones.detail", exh_exhorto_promocion_id=resultado.id),
                },
                "fecha_origen": resultado.fecha_origen.strftime("%Y-%m-%d %H:%M"),
                "remitente": resultado.remitente,
                "fojas": resultado.fojas,
                "observaciones": resultado.observaciones,
                "estado": resultado.estado,
                "creado": resultado.creado.strftime("%Y-%m-%d %H:%M:%S"),
            }
        )
    # Entregar JSON
    return output_datatable_json(draw, total, data)


@exh_exhortos_promociones.route("/exh_exhortos_promociones")
def list_active():
    """Listado de promociones activas"""
    return render_template(
        "exh_exhortos_promociones/list.jinja2",
        filtros=json.dumps({"estatus": "A"}),
        titulo="Exhortos Promociones",
        remitentes=ExhExhortoPromocion.REMITENTES,
        estatus="A",
    )


@exh_exhortos_promociones.route("/exh_exhortos_promociones/inactivos")
@permission_required(MODULO, Permiso.ADMINISTRAR)
def list_inactive():
    """Listado de promociones inactivas"""
    return render_template(
        "exh_exhortos_promociones/list.jinja2",
        filtros=json.dumps({"estatus": "B"}),
        titulo="Exhortos Promociones inactivas",
        remitentes=ExhExhortoPromocion.REMITENTES,
        estatus="B",
    )


@exh_exhortos_promociones.route("/exh_exhortos_promociones/<int:exh_exhorto_promocion_id>")
def detail(exh_exhorto_promocion_id):
    """Detalle de una promoción"""
    exh_exhorto_promocion = ExhExhortoPromocion.query.get_or_404(exh_exhorto_promocion_id)
    # Consultar el municipio de origen porque NO es una relacion
    municipio_destino = Municipio.query.filter_by(id=exh_exhorto_promocion.exh_exhorto.municipio_destino_id).first()
    estado = municipio_destino.estado.nombre
    return render_template("exh_exhortos_promociones/detail.jinja2", exh_exhorto_promocion=exh_exhorto_promocion, estado=estado)


@exh_exhortos_promociones.route("/exh_exhortos_promociones/nuevo/<int:exh_exhorto_id>", methods=["GET", "POST"])
@permission_required(MODULO, Permiso.CREAR)
def new_with_exh_exhorto(exh_exhorto_id):
    """Nueva promoción con el ID de un exhorto"""
    exh_exhorto = ExhExhorto.query.get_or_404(exh_exhorto_id)

    form = ExhExhortoPromocionForm()
    if form.validate_on_submit():
        # Insertar el registro ExhExhortoPromocion
        exh_exhorto_promocion = ExhExhortoPromocion(
            exh_exhorto=exh_exhorto,
            folio_origen_promocion=form.folio_origen.data,
            fecha_origen=datetime.now(),
            fojas=form.fojas.data,
            remitente="INTERNO",
            estado="PENDIENTE",
            observaciones=safe_string(form.observaciones.data, save_enie=True, max_len=1024),
        )
        exh_exhorto_promocion.save()

        # Insertar en la Bitácora
        bitacora = Bitacora(
            modulo=Modulo.query.filter_by(nombre=MODULO).first(),
            usuario=current_user,
            descripcion=safe_message(f"Nueva Promoción {exh_exhorto_promocion.id}"),
            url=url_for("exh_exhortos_promociones.detail", exh_exhorto_promocion_id=exh_exhorto_promocion.id),
        )
        bitacora.save()

        # Mostrar mensaje de éxito y redirigir a la página del detalle del ExhExhorto
        flash(bitacora.descripcion, "success")
        return redirect(url_for("exh_exhortos_promociones.detail", exh_exhorto_promocion_id=exh_exhorto_promocion.id))

    # Entregar el formulario
    form.folio_origen.data = generar_identificador()
    return render_template("exh_exhortos_promociones/new_with_exh_exhorto.jinja2", form=form, exh_exhorto=exh_exhorto)


@exh_exhortos_promociones.route("/exh_exhortos_promociones/edicion/<int:exh_exhorto_promocion_id>", methods=["GET", "POST"])
@permission_required(MODULO, Permiso.MODIFICAR)
def edit(exh_exhorto_promocion_id):
    """Editar una promoción"""
    exh_exhorto_promocion = ExhExhortoPromocion.query.get_or_404(exh_exhorto_promocion_id)
    form = ExhExhortoPromocionForm()
    if form.validate_on_submit():
        exh_exhorto_promocion.fojas = form.fojas.data
        exh_exhorto_promocion.observaciones = safe_string(form.observaciones.data, max_len=1024)
        exh_exhorto_promocion.save()
        bitacora = Bitacora(
            modulo=Modulo.query.filter_by(nombre=MODULO).first(),
            usuario=current_user,
            descripcion=safe_message(f"Editado Promoción {exh_exhorto_promocion.folio_origen_promocion}"),
            url=url_for("exh_exhortos_promociones.detail", exh_exhorto_promocion_id=exh_exhorto_promocion.id),
        )
        bitacora.save()
        flash(bitacora.descripcion, "success")
        return redirect(bitacora.url)
    form.fojas.data = exh_exhorto_promocion.fojas
    form.observaciones.data = exh_exhorto_promocion.observaciones
    return render_template("exh_exhortos_promociones/edit.jinja2", form=form, exh_exhorto_promocion=exh_exhorto_promocion)


@exh_exhortos_promociones.route("/exh_exhortos_promociones/eliminar/<int:exh_exhorto_promocion_id>")
@permission_required(MODULO, Permiso.ADMINISTRAR)
def delete(exh_exhorto_promocion_id):
    """Eliminar una promoción"""
    exh_exhorto_promocion = ExhExhortoPromocion.query.get_or_404(exh_exhorto_promocion_id)
    if exh_exhorto_promocion.estatus == "A":
        exh_exhorto_promocion.delete()
        bitacora = Bitacora(
            modulo=Modulo.query.filter_by(nombre=MODULO).first(),
            usuario=current_user,
            descripcion=safe_message(f"Eliminado Promoción {exh_exhorto_promocion.id}"),
            url=url_for("exh_exhortos_promociones.detail", exh_exhorto_promocion_id=exh_exhorto_promocion.id),
        )
        bitacora.save()
        flash(bitacora.descripcion, "success")
    return redirect(url_for("exh_exhortos_promociones.detail", exh_exhorto_promocion_id=exh_exhorto_promocion.id))


@exh_exhortos_promociones.route("/exh_exhortos_promociones/recuperar/<int:exh_exhorto_promocion_id>")
@permission_required(MODULO, Permiso.ADMINISTRAR)
def recover(exh_exhorto_promocion_id):
    """Recuperar una promoción"""
    exh_exhorto_promocion = ExhExhortoPromocion.query.get_or_404(exh_exhorto_promocion_id)
    if exh_exhorto_promocion.estatus == "B":
        exh_exhorto_promocion.recover()
        bitacora = Bitacora(
            modulo=Modulo.query.filter_by(nombre=MODULO).first(),
            usuario=current_user,
            descripcion=safe_message(f"Recuperado Promoción {exh_exhorto_promocion.id}"),
            url=url_for("exh_exhortos_promociones.detail", exh_exhorto_promocion_id=exh_exhorto_promocion.id),
        )
        bitacora.save()
        flash(bitacora.descripcion, "success")
    return redirect(url_for("exh_exhortos_promociones.detail", exh_exhorto_promocion_id=exh_exhorto_promocion.id))


@exh_exhortos_promociones.route("/exh_exhortos_promociones/enviar/<int:exh_exhorto_promocion_id>")
@permission_required(MODULO, Permiso.MODIFICAR)
def launch_task_send(exh_exhorto_promocion_id):
    """Lanzar tarea en el fondo para enviar una promoción al PJ Externo"""
    exh_exhorto_promocion = ExhExhortoPromocion.query.get_or_404(exh_exhorto_promocion_id)
    # Validar el estado
    if exh_exhorto_promocion.estado != "PENDIENTE":
        flash("El estado de la promoción debe ser PENDIENTE.", "warning")
        return redirect(url_for("exh_exhortos_promociones.detail", exh_exhorto_promocion_id=exh_exhorto_promocion.id))
    # Lanzar tarea en el fondo
    tarea = current_user.launch_task(
        comando="exh_exhortos_promociones.tasks.task_enviar_promocion",
        mensaje="Enviando la promoción al PJ externo",
        exh_exhorto_promocion_id=exh_exhorto_promocion_id,
    )
    flash("Se ha lanzado la tarea en el fondo. Esta página se va a recargar en 10 segundos...", "info")
    return redirect(url_for("tareas.detail", tarea_id=tarea.id))


@exh_exhortos_promociones.route("/exh_exhortos_promociones/cancelar/<int:exh_exhorto_promocion_id>")
@permission_required(MODULO, Permiso.MODIFICAR)
def change_to_cancel(exh_exhorto_promocion_id):
    """Cancelar una promoción"""
    exh_exhorto_promocion = ExhExhortoPromocion.query.get_or_404(exh_exhorto_promocion_id)
    if exh_exhorto_promocion.estado == "PENDIENTE":
        exh_exhorto_promocion.estado = "CANCELADO"
        exh_exhorto_promocion.save()
        bitacora = Bitacora(
            modulo=Modulo.query.filter_by(nombre=MODULO).first(),
            usuario=current_user,
            descripcion=safe_message(f"Promoción Cancelada {exh_exhorto_promocion.folio_origen_promocion}"),
            url=url_for("exh_exhortos_promociones.detail", exh_exhorto_promocion_id=exh_exhorto_promocion.id),
        )
        bitacora.save()
        flash(bitacora.descripcion, "success")
    return redirect(url_for("exh_exhortos_promociones.detail", exh_exhorto_promocion_id=exh_exhorto_promocion.id))
