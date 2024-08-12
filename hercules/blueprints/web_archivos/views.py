"""
Web Archivos, vistas
"""

import json

from flask import Blueprint, flash, redirect, render_template, request, url_for
from flask_login import current_user, login_required

from hercules.blueprints.bitacoras.models import Bitacora
from hercules.blueprints.modulos.models import Modulo
from hercules.blueprints.permisos.models import Permiso
from hercules.blueprints.usuarios.decorators import permission_required
from hercules.blueprints.web_archivos.forms import WebArchivoForm
from hercules.blueprints.web_archivos.models import WebArchivo
from hercules.blueprints.web_paginas.models import WebPagina
from lib.datatables import get_datatable_parameters, output_datatable_json
from lib.safe_string import safe_clave, safe_message, safe_string, safe_url

MODULO = "WEB ARCHIVOS"

web_archivos = Blueprint("web_archivos", __name__, template_folder="templates")


@web_archivos.before_request
@login_required
@permission_required(MODULO, Permiso.VER)
def before_request():
    """Permiso por defecto"""


@web_archivos.route("/web_archivos/datatable_json", methods=["GET", "POST"])
def datatable_json():
    """DataTable JSON para listado de WebArchivos"""
    # Tomar parámetros de Datatables
    draw, start, rows_per_page = get_datatable_parameters()
    # Consultar
    consulta = WebArchivo.query
    # Primero filtrar por columnas propias
    if "estatus" in request.form:
        consulta = consulta.filter_by(estatus=request.form["estatus"])
    else:
        consulta = consulta.filter_by(estatus="A")
    if "web_pagina_id" in request.form:
        consulta = consulta.filter_by(web_pagina_id=request.form["web_pagina_id"])
    if "clave" in request.form:
        clave = safe_clave(request.form["clave"])
        if clave != "":
            consulta = consulta.filter(WebArchivo.clave.contains(clave))
    if "descripcion" in request.form:
        descripcion = safe_string(request.form["descripcion"], do_unidecode=False, save_enie=True, to_uppercase=False)
        if descripcion != "":
            consulta = consulta.filter(WebArchivo.descripcion.contains(descripcion))
    # Ordenar y paginar
    registros = consulta.order_by(WebArchivo.clave).offset(start).limit(rows_per_page).all()
    total = consulta.count()
    # Elaborar datos para DataTable
    data = []
    for resultado in registros:
        data.append(
            {
                "web_pagina_clave": resultado.web_pagina.clave,
                "detalle": {
                    "clave": resultado.clave,
                    "url": url_for("web_archivos.detail", web_archivo_id=resultado.id),
                },
                "archivo": resultado.archivo,
                "descripcion": resultado.descripcion,
            }
        )
    # Entregar JSON
    return output_datatable_json(draw, total, data)


@web_archivos.route("/web_archivos")
def list_active():
    """Listado de WebArchivos activos"""
    return render_template(
        "web_archivos/list.jinja2",
        filtros=json.dumps({"estatus": "A"}),
        titulo="Archivos",
        estatus="A",
    )


@web_archivos.route("/web_archivos/inactivos")
@permission_required(MODULO, Permiso.ADMINISTRAR)
def list_inactive():
    """Listado de WebArchivos inactivos"""
    return render_template(
        "web_archivos/list.jinja2",
        filtros=json.dumps({"estatus": "B"}),
        titulo="Archivos inactivos",
        estatus="B",
    )


@web_archivos.route("/web_archivos/<int:web_archivo_id>")
def detail(web_archivo_id):
    """Detalle de un WebArchivo"""
    web_archivo = WebArchivo.query.get_or_404(web_archivo_id)
    return render_template("web_archivos/detail.jinja2", web_archivo=web_archivo)


@web_archivos.route("/web_archivos/nuevo/<int:web_pagina_id>", methods=["GET", "POST"])
@permission_required(MODULO, Permiso.CREAR)
def new(web_pagina_id):
    """Nuevo WebArchivo"""
    web_pagina = WebPagina.query.get_or_404(web_pagina_id)
    form = WebArchivoForm()
    if form.validate_on_submit():
        # Validar que la clave no está en uso
        clave = safe_clave(form.clave.data)
        if WebArchivo.query.filter_by(clave=clave).first():
            flash(f"La clave {clave} ya está en uso", "warning")
            return render_template("web_archivos/new.jinja2", form=form, web_pagina=web_pagina)
        # Guardar
        web_archivo = WebArchivo(
            web_pagina_id=web_pagina.id,
            descripcion=safe_string(form.descripcion.data, do_unidecode=False, save_enie=True, to_uppercase=False),
            clave=clave,
            archivo=safe_string(form.archivo.data, to_uppercase=False),
            url=safe_url(form.url.data),
        )
        web_archivo.save()
        bitacora = Bitacora(
            modulo=Modulo.query.filter_by(nombre=MODULO).first(),
            usuario=current_user,
            descripcion=safe_message(f"Nuevo Archivo {web_archivo.clave} en Pagina {web_pagina.titulo}"),
            url=url_for("web_archivos.detail", web_archivo_id=web_archivo.id),
        )
        bitacora.save()
        flash(bitacora.descripcion, "success")
        return redirect(bitacora.url)
    # Poner valores por defecto
    form.clave.data = web_pagina.clave + "-"
    return render_template("web_archivos/new.jinja2", form=form, web_pagina=web_pagina)


@web_archivos.route("/web_archivos/edicion/<int:web_archivo_id>", methods=["GET", "POST"])
@permission_required(MODULO, Permiso.MODIFICAR)
def edit(web_archivo_id):
    """Editar WebArchivo"""
    web_archivo = WebArchivo.query.get_or_404(web_archivo_id)
    form = WebArchivoForm()
    if form.validate_on_submit():
        es_valido = True
        # Si cambia la clave, validar que la clave no está en uso
        clave = safe_clave(form.clave.data)
        if web_archivo.clave != clave and WebArchivo.query.filter_by(clave=clave).first():
            flash("La clave ya está en uso", "warning")
            es_valido = False
        # Si es válido
        if es_valido:
            # Guardar
            web_archivo.descripcion = safe_string(form.descripcion.data, do_unidecode=False, save_enie=True, to_uppercase=False)
            web_archivo.clave = clave
            web_archivo.archivo = safe_string(form.archivo.data, to_uppercase=False)
            web_archivo.url = safe_url(form.url.data)
            web_archivo.save()
            # Guardar bitácora
            bitacora = Bitacora(
                modulo=Modulo.query.filter_by(nombre=MODULO).first(),
                usuario=current_user,
                descripcion=safe_message(f"Editado Archivo {web_archivo.clave} en Pagina {web_archivo.web_pagina.clave}"),
                url=url_for("web_archivos.detail", web_archivo_id=web_archivo.id),
            )
            bitacora.save()
            # Entregar detalle
            flash(bitacora.descripcion, "success")
            return redirect(bitacora.url)
    form.descripcion.data = web_archivo.descripcion
    form.clave.data = web_archivo.clave
    form.archivo.data = web_archivo.archivo
    form.url.data = web_archivo.url
    return render_template("web_archivos/edit.jinja2", form=form, web_archivo=web_archivo)


@web_archivos.route("/web_archivos/eliminar/<int:web_archivo_id>")
@permission_required(MODULO, Permiso.ADMINISTRAR)
def delete(web_archivo_id):
    """Eliminar WebArchivo"""
    web_archivo = WebArchivo.query.get_or_404(web_archivo_id)
    if web_archivo.estatus == "A":
        web_archivo.delete()
        bitacora = Bitacora(
            modulo=Modulo.query.filter_by(nombre=MODULO).first(),
            usuario=current_user,
            descripcion=safe_message(f"Eliminado Archivo {web_archivo.clave} de Pagina {web_archivo.web_pagina.clave}"),
            url=url_for("web_archivos.detail", web_archivo_id=web_archivo.id),
        )
        bitacora.save()
        flash(bitacora.descripcion, "success")
    return redirect(url_for("web_archivos.detail", web_archivo_id=web_archivo.id))


@web_archivos.route("/web_archivos/recuperar/<int:web_archivo_id>")
@permission_required(MODULO, Permiso.ADMINISTRAR)
def recover(web_archivo_id):
    """Recuperar WebArchivo"""
    web_archivo = WebArchivo.query.get_or_404(web_archivo_id)
    if web_archivo.estatus == "B":
        web_archivo.recover()
        bitacora = Bitacora(
            modulo=Modulo.query.filter_by(nombre=MODULO).first(),
            usuario=current_user,
            descripcion=safe_message(f"Recuperado Archivo {web_archivo.clave} de Pagina {web_archivo.web_pagina.clave}"),
            url=url_for("web_archivos.detail", instance_id=web_archivo.id),
        )
        bitacora.save()
        flash(bitacora.descripcion, "success")
    return redirect(url_for("web_archivos.detail", web_archivo_id=web_archivo.id))
