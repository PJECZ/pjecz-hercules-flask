"""
Oficinas, vistas
"""

import json
from flask import Blueprint, flash, redirect, render_template, request, url_for
from flask_login import current_user, login_required

from lib.datatables import get_datatable_parameters, output_datatable_json
from lib.safe_string import safe_clave, safe_string, safe_message

from hercules.blueprints.bitacoras.models import Bitacora
from hercules.blueprints.modulos.models import Modulo
from hercules.blueprints.oficinas.forms import OficinaForm
from hercules.blueprints.oficinas.models import Oficina
from hercules.blueprints.permisos.models import Permiso
from hercules.blueprints.usuarios.decorators import permission_required

MODULO = "OFICINAS"

oficinas = Blueprint("oficinas", __name__, template_folder="templates")


@oficinas.before_request
@login_required
@permission_required(MODULO, Permiso.VER)
def before_request():
    """Permiso por defecto"""


@oficinas.route("/oficinas/datatable_json", methods=["GET", "POST"])
def datatable_json():
    """DataTable JSON para listado de Oficinas"""
    # Tomar parámetros de Datatables
    draw, start, rows_per_page = get_datatable_parameters()
    # Consultar
    consulta = Oficina.query
    # Primero filtrar por columnas propias
    if "estatus" in request.form:
        consulta = consulta.filter_by(estatus=request.form["estatus"])
    else:
        consulta = consulta.filter_by(estatus="A")
    if "distrito_id" in request.form:
        consulta = consulta.filter(Oficina.distrito_id == request.form["distrito_id"])
    if "domicilio_id" in request.form:
        consulta = consulta.filter_by(domicilio_id=request.form["domicilio_id"])
    if "clave" in request.form:
        try:
            clave = safe_clave(request.form["clave"])
            if clave != "":
                consulta = consulta.filter(Oficina.clave.contains(clave))
        except ValueError:
            pass
    if "descripcion_corta" in request.form:
        descripcion_corta = safe_string(request.form["descripcion_corta"], save_enie=True)
        if descripcion_corta != "":
            consulta = consulta.filter(Oficina.descripcion_corta.contains(descripcion_corta))
    # Luego filtrar por columnas de otras tablas
    # if "persona_rfc" in request.form:
    #     consulta = consulta.join(Persona)
    #     consulta = consulta.filter(Persona.rfc.contains(safe_rfc(request.form["persona_rfc"], search_fragment=True)))
    # Ordenar y paginar
    registros = consulta.order_by(Oficina.clave).offset(start).limit(rows_per_page).all()
    total = consulta.count()
    # Elaborar datos para DataTable
    data = []
    for resultado in registros:
        data.append(
            {
                "detalle": {
                    "clave": resultado.clave,
                    "url": url_for("oficinas.detail", oficina_id=resultado.id),
                },
                "descripcion_corta": resultado.descripcion_corta,
                "domicilio": {
                    "completo": resultado.domicilio.completo,
                    "url": (
                        url_for("domicilios.detail", domicilio_id=resultado.domicilio_id)
                        if current_user.can_view("DOMICILIOS")
                        else ""
                    ),
                },
                "distrito": {
                    "nombre_corto": resultado.distrito.nombre_corto,
                    "url": (
                        url_for("distritos.detail", distrito_id=resultado.distrito_id)
                        if current_user.can_view("DISTRITOS")
                        else ""
                    ),
                },
                "apertura": resultado.apertura.strftime("%H:%M"),
                "cierre": resultado.cierre.strftime("%H:%M"),
                "limite_personas": resultado.limite_personas,
                "es_jurisdiccional": resultado.es_jurisdiccional,
                "puede_agendar_citas": resultado.puede_agendar_citas,
                "puede_enviar_qr": resultado.puede_enviar_qr,
            }
        )
    # Entregar JSON
    return output_datatable_json(draw, total, data)


@oficinas.route("/oficinas")
def list_active():
    """Listado de Oficina activas"""
    return render_template(
        "oficinas/list.jinja2",
        filtros=json.dumps({"estatus": "A"}),
        titulo="Oficina",
        estatus="A",
    )


@oficinas.route("/oficinas/inactivos")
@permission_required(MODULO, Permiso.ADMINISTRAR)
def list_inactive():
    """Listado de Oficinas inactivas"""
    return render_template(
        "oficinas/list.jinja2",
        filtros=json.dumps({"estatus": "B"}),
        titulo="Oficinas inactivos",
        estatus="B",
    )


@oficinas.route("/oficinas/<int:oficina_id>")
def detail(oficina_id):
    """Detalle de una Oficina"""
    oficina = Oficina.query.get_or_404(oficina_id)
    return render_template("oficinas/detail.jinja2", oficina=oficina)


@oficinas.route("/oficinas/nuevo", methods=["GET", "POST"])
@permission_required(MODULO, Permiso.CREAR)
def new():
    """Nueva Oficina"""
    form = OficinaForm()
    if form.validate_on_submit():
        # Validar que la clave no se repita
        clave = safe_clave(form.clave.data, max_len=32)
        if Oficina.query.filter_by(clave=clave).first():
            flash("La clave ya está en uso. Debe de ser única.", "warning")
            return render_template("oficinas/new.jinja2", form=form)
        # Guardar
        oficina = Oficina(
            distrito_id=form.distrito.data,
            domicilio_id=form.domicilio.data,
            clave=clave,
            descripcion=safe_string(form.descripcion.data, max_len=512, save_enie=True),
            descripcion_corta=safe_string(form.descripcion_corta.data, max_len=64, save_enie=True),
            es_jurisdiccional=form.es_jurisdiccional.data,
            puede_agendar_citas=form.puede_agendar_citas.data,
            apertura=form.apertura.data,
            cierre=form.cierre.data,
            limite_personas=form.limite_personas.data,
            puede_enviar_qr=form.puede_enviar_qr.data,
        )
        oficina.save()
        bitacora = Bitacora(
            modulo=Modulo.query.filter_by(nombre=MODULO).first(),
            usuario=current_user,
            descripcion=safe_message(f"Nuevo Oficina {oficina.clave}"),
            url=url_for("oficinas.detail", oficina_id=oficina.id),
        )
        bitacora.save()
        flash(bitacora.descripcion, "success")
        return redirect(bitacora.url)
    return render_template("oficinas/new.jinja2", form=form)


@oficinas.route("/oficinas/edicion/<int:oficina_id>", methods=["GET", "POST"])
@permission_required(MODULO, Permiso.MODIFICAR)
def edit(oficina_id):
    """Editar Oficina"""
    oficina = Oficina.query.get_or_404(oficina_id)
    form = OficinaForm()
    if form.validate_on_submit():
        es_valido = True
        # Si cambia la clave verificar que no este en uso
        clave = safe_clave(form.clave.data, max_len=32)
        if oficina.clave != clave:
            oficina_existente = Oficina.query.filter_by(clave=clave).first()
            if oficina_existente and oficina_existente.id != oficina_id:
                es_valido = False
                flash("La clave ya está en uso. Debe de ser única.", "warning")
        # Si es valido actualizar
        if es_valido:
            oficina.distrito_id = form.distrito.data
            oficina.domicilio_id = form.domicilio.data
            oficina.clave = clave
            oficina.descripcion = safe_string(form.descripcion.data, max_len=512, save_enie=True)
            oficina.descripcion_corta = safe_string(form.descripcion_corta.data, max_len=64, save_enie=True)
            oficina.es_jurisdiccional = form.es_jurisdiccional.data
            oficina.puede_agendar_citas = form.puede_agendar_citas.data
            oficina.apertura = form.apertura.data
            oficina.cierre = form.cierre.data
            oficina.limite_personas = form.limite_personas.data
            oficina.puede_enviar_qr = form.puede_enviar_qr.data
            oficina.save()
            bitacora = Bitacora(
                modulo=Modulo.query.filter_by(nombre=MODULO).first(),
                usuario=current_user,
                descripcion=safe_message(f"Editado Oficina {oficina.clave}"),
                url=url_for("oficinas.detail", oficina_id=oficina.id),
            )
            bitacora.save()
            flash(bitacora.descripcion, "success")
            return redirect(bitacora.url)
    form.distrito.data = oficina.distrito_id  # Se manda distrito_id porque es un select
    form.domicilio.data = oficina.domicilio_id  # Se manda domicilio_id porque es un select
    form.clave.data = oficina.clave
    form.descripcion_corta.data = oficina.descripcion_corta
    form.descripcion.data = oficina.descripcion
    form.es_jurisdiccional.data = oficina.es_jurisdiccional
    form.puede_agendar_citas.data = oficina.puede_agendar_citas
    form.apertura.data = oficina.apertura
    form.cierre.data = oficina.cierre
    form.limite_personas.data = oficina.limite_personas
    form.puede_enviar_qr.data = oficina.puede_enviar_qr
    form.clave.data = oficina.clave
    return render_template("oficinas/edit.jinja2", form=form, oficina=oficina)


@oficinas.route("/oficinas/eliminar/<int:oficina_id>")
@permission_required(MODULO, Permiso.ADMINISTRAR)
def delete(oficina_id):
    """Eliminar Oficina"""
    oficina = Oficina.query.get_or_404(oficina_id)
    if oficina.estatus == "A":
        oficina.delete()
        bitacora = Bitacora(
            modulo=Modulo.query.filter_by(nombre=MODULO).first(),
            usuario=current_user,
            descripcion=safe_message(f"Eliminado Oficina {oficina.clave}"),
            url=url_for("oficinas.detail", oficina_id=oficina.id),
        )
        bitacora.save()
        flash(bitacora.descripcion, "success")
    return redirect(url_for("oficinas.detail", oficina_id=oficina.id))
