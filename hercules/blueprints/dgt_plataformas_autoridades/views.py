"""
DGT Plataformas Autoridades, vistas
"""

import json

from flask import Blueprint, flash, redirect, render_template, request, url_for
from flask_login import current_user, login_required
from sqlalchemy import or_
from sqlalchemy.exc import IntegrityError

from hercules.blueprints.autoridades.models import Autoridad
from hercules.blueprints.bitacoras.models import Bitacora
from hercules.blueprints.dgt_plataformas.models import DgtPlataforma
from hercules.blueprints.dgt_plataformas_autoridades.models import DgtPlataformaAutoridad
from hercules.blueprints.modulos.models import Modulo
from hercules.blueprints.permisos.models import Permiso
from hercules.blueprints.usuarios.decorators import permission_required
from hercules.extensions import database
from lib.datatables import get_datatable_parameters, output_datatable_json
from lib.safe_string import safe_clave, safe_message, safe_string, safe_uuid

MODULO = "DGT PLATAFORMAS AUTORIDADES"

dgt_plataformas_autoridades = Blueprint("dgt_plataformas_autoridades", __name__, template_folder="templates")


@dgt_plataformas_autoridades.before_request
@login_required
@permission_required(MODULO, Permiso.VER)
def before_request():
    """Permiso por defecto"""


@dgt_plataformas_autoridades.route("/dgt_plataformas_autoridades/datatable_json", methods=["GET", "POST"])
def datatable_json():
    """DataTable JSON para listado de DGT Plataformas Autoridades"""
    # Tomar parámetros de Datatables
    draw, start, rows_per_page = get_datatable_parameters()
    # Consultar
    consulta = DgtPlataformaAutoridad.query
    # Primero filtrar por columnas propias
    if "estatus" in request.form:
        consulta = consulta.filter(DgtPlataformaAutoridad.estatus == request.form["estatus"])
    else:
        consulta = consulta.filter(DgtPlataformaAutoridad.estatus == "A")
    if "dgt_plataforma_id" in request.form:
        dgt_plataforma_id = safe_uuid(request.form["dgt_plataforma_id"])
        if dgt_plataforma_id != "":
            consulta = consulta.filter(DgtPlataformaAutoridad.dgt_plataforma_id == dgt_plataforma_id)
    # Luego filtrar por columnas de otras tablas
    consulta = consulta.join(Autoridad)
    if "autoridad_clave" in request.form:
        try:
            autoridad_clave = safe_clave(request.form["autoridad_clave"])
            if autoridad_clave != "":
                consulta = consulta.filter(Autoridad.clave.contains(autoridad_clave))
        except ValueError:
            pass
    if "autoridad_descripcion" in request.form:
        autoridad_descripcion = safe_string(request.form["autoridad_descripcion"], save_enie=True)
        if autoridad_descripcion != "":
            consulta = consulta.filter(Autoridad.descripcion_corta.contains(autoridad_descripcion))
    if "dgt_plataforma_descripcion" in request.form:
        dgt_plataforma_descripcion = safe_string(request.form["dgt_plataforma_descripcion"], save_enie=True)
        if dgt_plataforma_descripcion != "":
            consulta = consulta.join(DgtPlataforma).filter(DgtPlataforma.descripcion.contains(dgt_plataforma_descripcion))
    # Ordenar y paginar
    registros = consulta.order_by(Autoridad.clave).offset(start).limit(rows_per_page).all()
    total = consulta.count()
    # Elaborar datos para DataTable
    puede_quitar = current_user.can_edit(MODULO)
    data = []
    for item in registros:
        data.append(
            {
                "detalle": {
                    "autoridad_clave": item.autoridad.clave,
                    "url": url_for("dgt_plataformas_autoridades.detail", dgt_plataforma_autoridad_id=item.id),
                },
                "autoridad_descripcion_corta": item.autoridad.descripcion_corta,
                "distrito_nombre_corto": item.autoridad.distrito.nombre_corto,
                "dgt_plataforma_descripcion": item.dgt_plataforma.descripcion,
                "quitar": {
                    "autoridad_clave": item.autoridad.clave,
                    "url": (
                        url_for("dgt_plataformas_autoridades.remove_json", dgt_plataforma_autoridad_id=item.id)
                        if puede_quitar and item.estatus == "A"
                        else ""
                    ),
                },
            }
        )
    # Entregar JSON
    return output_datatable_json(draw, total, data)


@dgt_plataformas_autoridades.route("/dgt_plataformas_autoridades")
def list_active():
    """Listado de DGT Plataformas Autoridades activas"""
    return render_template(
        "dgt_plataformas_autoridades/list.jinja2",
        filtros=json.dumps({"estatus": "A"}),
        titulo="DGT Plataformas Autoridades",
        estatus="A",
    )


@dgt_plataformas_autoridades.route("/dgt_plataformas_autoridades/inactivos")
@permission_required(MODULO, Permiso.ADMINISTRAR)
def list_inactive():
    """Listado de DGT Plataformas Autoridades inactivas"""
    return render_template(
        "dgt_plataformas_autoridades/list.jinja2",
        filtros=json.dumps({"estatus": "B"}),
        titulo="DGT Plataformas Autoridades inactivas",
        estatus="B",
    )


@dgt_plataformas_autoridades.route("/dgt_plataformas_autoridades/<dgt_plataforma_autoridad_id>")
def detail(dgt_plataforma_autoridad_id):
    """Detalle de una DGT Plataforma Autoridad"""
    dgt_plataforma_autoridad_id = safe_uuid(dgt_plataforma_autoridad_id)
    if dgt_plataforma_autoridad_id == "":
        flash("ID de DGT Plataforma Autoridad inválido", "warning")
        return redirect(url_for("dgt_plataformas_autoridades.list_active"))
    dgt_plataforma_autoridad = DgtPlataformaAutoridad.query.get_or_404(dgt_plataforma_autoridad_id)
    return render_template("dgt_plataformas_autoridades/detail.jinja2", dgt_plataforma_autoridad=dgt_plataforma_autoridad)


@dgt_plataformas_autoridades.route("/dgt_plataformas_autoridades/select2_json/<dgt_plataforma_id>", methods=["GET", "POST"])
@permission_required(MODULO, Permiso.CREAR)
def select2_json(dgt_plataforma_id):
    """JSON de autoridades para elegir con un Select2, marca como deshabilitadas las que ya tienen plataforma"""
    dgt_plataforma_id = safe_uuid(dgt_plataforma_id)
    if dgt_plataforma_id == "":
        return {"results": [], "pagination": {"more": False}}
    consulta = Autoridad.query.filter(Autoridad.estatus == "A")
    if "searchString" in request.form:
        texto = safe_string(request.form["searchString"], save_enie=True)
        if texto != "":
            consulta = consulta.filter(or_(Autoridad.clave.contains(texto), Autoridad.descripcion_corta.contains(texto)))
    resultados = []
    for autoridad in consulta.order_by(Autoridad.clave).limit(20).all():
        texto = f"{autoridad.clave}: {autoridad.descripcion_corta}"
        deshabilitado = False
        asignacion = autoridad.dgt_plataforma_autoridad
        if asignacion is not None and asignacion.estatus == "A":
            deshabilitado = True
            if str(asignacion.dgt_plataforma_id) == dgt_plataforma_id:
                texto += " (ya está en esta plataforma)"
            else:
                texto += f" (asignada a {asignacion.dgt_plataforma.descripcion})"
        resultados.append({"id": autoridad.id, "text": texto, "disabled": deshabilitado})
    return {"results": resultados, "pagination": {"more": False}}


@dgt_plataformas_autoridades.route("/dgt_plataformas_autoridades/agregar_json/<dgt_plataforma_id>", methods=["POST"])
@permission_required(MODULO, Permiso.CREAR)
def add_json(dgt_plataforma_id):
    """Agregar una o varias autoridades a una plataforma, respuesta JSON"""
    dgt_plataforma_id = safe_uuid(dgt_plataforma_id)
    if dgt_plataforma_id == "":
        return {"success": False, "message": "ID de DGT Plataforma inválido"}
    dgt_plataforma = DgtPlataforma.query.get(dgt_plataforma_id)
    if dgt_plataforma is None or dgt_plataforma.estatus != "A":
        return {"success": False, "message": "La DGT Plataforma no existe o está eliminada"}
    # Tomar los IDs de las autoridades
    autoridades_ids = []
    for valor in request.form.getlist("autoridades_ids"):
        try:
            autoridades_ids.append(int(valor))
        except ValueError:
            pass
    if len(autoridades_ids) == 0:
        return {"success": False, "message": "No se eligió ninguna autoridad"}
    # Asignar cada autoridad
    agregadas = []
    omitidas = []
    for autoridad_id in autoridades_ids:
        autoridad = Autoridad.query.get(autoridad_id)
        if autoridad is None or autoridad.estatus != "A":
            omitidas.append(f"ID {autoridad_id}: no existe o está eliminada")
            continue
        try:
            dgt_plataforma_autoridad, hubo_cambios = DgtPlataformaAutoridad.asignar(autoridad.id, dgt_plataforma.id)
        except ValueError as error:
            omitidas.append(f"{autoridad.clave}: {error}")
            continue
        except IntegrityError:
            # La base de datos rechazó una autoridad duplicada (otra persona la asignó al mismo tiempo)
            database.session.rollback()
            omitidas.append(f"{autoridad.clave}: ya tiene una plataforma asignada")
            continue
        if not hubo_cambios:
            omitidas.append(f"{autoridad.clave}: ya está en esta plataforma")
            continue
        agregadas.append(autoridad.clave)
        Bitacora(
            modulo=Modulo.query.filter_by(nombre=MODULO).first(),
            usuario=current_user,
            descripcion=safe_message(f"Agregada la autoridad {autoridad.clave} a la DGT Plataforma {dgt_plataforma.descripcion}"),
            url=url_for("dgt_plataformas_autoridades.detail", dgt_plataforma_autoridad_id=dgt_plataforma_autoridad.id),
        ).save()
    # Entregar JSON
    if len(agregadas) > 0:
        mensaje = f"Se agregaron {len(agregadas)} autoridades: {', '.join(agregadas)}"
    else:
        mensaje = "No se agregó ninguna autoridad"
    return {"success": len(agregadas) > 0, "message": mensaje, "agregadas": agregadas, "omitidas": omitidas}


@dgt_plataformas_autoridades.route("/dgt_plataformas_autoridades/quitar_json/<dgt_plataforma_autoridad_id>", methods=["POST"])
@permission_required(MODULO, Permiso.MODIFICAR)
def remove_json(dgt_plataforma_autoridad_id):
    """Quitar una autoridad de su plataforma, respuesta JSON"""
    dgt_plataforma_autoridad_id = safe_uuid(dgt_plataforma_autoridad_id)
    if dgt_plataforma_autoridad_id == "":
        return {"success": False, "message": "ID de DGT Plataforma Autoridad inválido"}
    dgt_plataforma_autoridad = DgtPlataformaAutoridad.query.get(dgt_plataforma_autoridad_id)
    if dgt_plataforma_autoridad is None:
        return {"success": False, "message": "No encontrado"}
    if dgt_plataforma_autoridad.estatus != "A":
        return {"success": False, "message": "Ya estaba quitada"}
    dgt_plataforma_autoridad.delete()
    bitacora = Bitacora(
        modulo=Modulo.query.filter_by(nombre=MODULO).first(),
        usuario=current_user,
        descripcion=safe_message(
            f"Quitada la autoridad {dgt_plataforma_autoridad.autoridad.clave} "
            f"de la DGT Plataforma {dgt_plataforma_autoridad.dgt_plataforma.descripcion}"
        ),
        url=url_for("dgt_plataformas_autoridades.detail", dgt_plataforma_autoridad_id=dgt_plataforma_autoridad.id),
    )
    bitacora.save()
    return {"success": True, "message": bitacora.descripcion}


@dgt_plataformas_autoridades.route("/dgt_plataformas_autoridades/eliminar/<dgt_plataforma_autoridad_id>")
@permission_required(MODULO, Permiso.ADMINISTRAR)
def delete(dgt_plataforma_autoridad_id):
    """Eliminar DGT Plataforma Autoridad"""
    dgt_plataforma_autoridad_id = safe_uuid(dgt_plataforma_autoridad_id)
    if dgt_plataforma_autoridad_id == "":
        flash("ID de DGT Plataforma Autoridad inválido", "warning")
        return redirect(url_for("dgt_plataformas_autoridades.list_active"))
    dgt_plataforma_autoridad = DgtPlataformaAutoridad.query.get_or_404(dgt_plataforma_autoridad_id)
    if dgt_plataforma_autoridad.estatus == "A":
        dgt_plataforma_autoridad.delete()
        bitacora = Bitacora(
            modulo=Modulo.query.filter_by(nombre=MODULO).first(),
            usuario=current_user,
            descripcion=safe_message(f"Eliminada DGT Plataforma Autoridad {dgt_plataforma_autoridad.autoridad.clave}"),
            url=url_for("dgt_plataformas_autoridades.detail", dgt_plataforma_autoridad_id=dgt_plataforma_autoridad.id),
        )
        bitacora.save()
        flash(bitacora.descripcion, "success")
    return redirect(url_for("dgt_plataformas_autoridades.detail", dgt_plataforma_autoridad_id=dgt_plataforma_autoridad.id))


@dgt_plataformas_autoridades.route("/dgt_plataformas_autoridades/recuperar/<dgt_plataforma_autoridad_id>")
@permission_required(MODULO, Permiso.ADMINISTRAR)
def recover(dgt_plataforma_autoridad_id):
    """Recuperar DGT Plataforma Autoridad"""
    dgt_plataforma_autoridad_id = safe_uuid(dgt_plataforma_autoridad_id)
    if dgt_plataforma_autoridad_id == "":
        flash("ID de DGT Plataforma Autoridad inválido", "warning")
        return redirect(url_for("dgt_plataformas_autoridades.list_active"))
    dgt_plataforma_autoridad = DgtPlataformaAutoridad.query.get_or_404(dgt_plataforma_autoridad_id)
    if dgt_plataforma_autoridad.estatus == "B":
        # No recuperar si la plataforma está eliminada
        if dgt_plataforma_autoridad.dgt_plataforma.estatus != "A":
            flash("No se puede recuperar porque la DGT Plataforma está eliminada", "warning")
            return redirect(
                url_for("dgt_plataformas_autoridades.detail", dgt_plataforma_autoridad_id=dgt_plataforma_autoridad.id)
            )
        dgt_plataforma_autoridad.recover()
        bitacora = Bitacora(
            modulo=Modulo.query.filter_by(nombre=MODULO).first(),
            usuario=current_user,
            descripcion=safe_message(f"Recuperada DGT Plataforma Autoridad {dgt_plataforma_autoridad.autoridad.clave}"),
            url=url_for("dgt_plataformas_autoridades.detail", dgt_plataforma_autoridad_id=dgt_plataforma_autoridad.id),
        )
        bitacora.save()
        flash(bitacora.descripcion, "success")
    return redirect(url_for("dgt_plataformas_autoridades.detail", dgt_plataforma_autoridad_id=dgt_plataforma_autoridad.id))
