"""
Web Paginas, vistas
"""

import json
from datetime import date

from flask import Blueprint, flash, redirect, render_template, request, url_for
from flask_login import current_user, login_required

from hercules.blueprints.bitacoras.models import Bitacora
from hercules.blueprints.modulos.models import Modulo
from hercules.blueprints.permisos.models import Permiso
from hercules.blueprints.usuarios.decorators import permission_required
from hercules.blueprints.web_paginas.forms import WebPaginaForm
from hercules.blueprints.web_paginas.forms import WebPaginaContenidoForm
from hercules.blueprints.web_paginas.models import WebPagina
from hercules.blueprints.web_ramas.models import WebRama
from lib.datatables import get_datatable_parameters, output_datatable_json
from lib.safe_string import safe_clave, safe_message, safe_string

MODULO = "WEB PAGINAS"

web_paginas = Blueprint("web_paginas", __name__, template_folder="templates")


@web_paginas.before_request
@login_required
@permission_required(MODULO, Permiso.VER)
def before_request():
    """Permiso por defecto"""


@web_paginas.route("/web_paginas/datatable_json", methods=["GET", "POST"])
def datatable_json():
    """DataTable JSON para listado de WebPaginas"""
    # Tomar parámetros de Datatables
    draw, start, rows_per_page = get_datatable_parameters()
    # Consultar
    consulta = WebPagina.query
    # Primero filtrar por columnas propias
    if "estatus" in request.form:
        consulta = consulta.filter_by(estatus=request.form["estatus"])
    else:
        consulta = consulta.filter_by(estatus="A")
    if "web_rama_id" in request.form:
        consulta = consulta.filter_by(web_rama_id=request.form["web_rama_id"])
    if "clave" in request.form:
        clave = safe_clave(request.form["clave"])
        if clave != "":
            consulta = consulta.filter(WebPagina.clave.contains(clave))
    if "titulo" in request.form:
        titulo = safe_string(request.form["titulo"], do_unidecode=False, save_enie=True, to_uppercase=False)
        if titulo != "":
            consulta = consulta.filter(WebPagina.titulo.contains(titulo))
    if "estado" in request.form:
        consulta = consulta.filter_by(estado=request.form["estado"])
    # Ordenar y paginar
    registros = consulta.order_by(WebPagina.clave).offset(start).limit(rows_per_page).all()
    total = consulta.count()
    # Elaborar datos para DataTable
    data = []
    for resultado in registros:
        data.append(
            {
                "web_rama_clave": resultado.web_rama.clave,
                "detalle": {
                    "clave": resultado.clave,
                    "url": url_for("web_paginas.detail", web_pagina_id=resultado.id),
                },
                "titulo": resultado.titulo,
                "fecha_modificacion": resultado.fecha_modificacion.strftime("%Y-%m-%d"),
                "estado": resultado.estado,
                "tiempo_publicar": resultado.tiempo_publicar.strftime("%Y-%m-%d %H:%M") if resultado.tiempo_publicar else "",
                "tiempo_archivar": resultado.tiempo_archivar.strftime("%Y-%m-%d %H:%M") if resultado.tiempo_archivar else "",
            }
        )
    # Entregar JSON
    return output_datatable_json(draw, total, data)


@web_paginas.route("/web_paginas")
def list_active():
    """Listado de WebPaginas activos"""
    return render_template(
        "web_paginas/list.jinja2",
        filtros=json.dumps({"estatus": "A"}),
        titulo="Páginas",
        estatus="A",
    )


@web_paginas.route("/web_paginas/inactivos")
@permission_required(MODULO, Permiso.ADMINISTRAR)
def list_inactive():
    """Listado de WebPaginas inactivas"""
    return render_template(
        "web_paginas/list.jinja2",
        filtros=json.dumps({"estatus": "B"}),
        titulo="Páginas inactivas",
        estatus="B",
    )


@web_paginas.route("/web_paginas/<int:web_pagina_id>")
def detail(web_pagina_id):
    """Detalle de una WebPagina"""
    web_pagina = WebPagina.query.get_or_404(web_pagina_id)
    return render_template("web_paginas/detail.jinja2", web_pagina=web_pagina)


@web_paginas.route("/web_paginas/nuevo/<int:web_rama_id>", methods=["GET", "POST"])
@permission_required(MODULO, Permiso.CREAR)
def new(web_rama_id):
    """Nueva WebPagina"""
    web_rama = WebRama.query.get_or_404(web_rama_id)
    form = WebPaginaNewForm()
    if form.validate_on_submit():
        # Validar que la clave no está en uso
        clave = safe_clave(form.clave.data)
        if WebPagina.query.filter_by(clave=clave).first():
            flash(f"La clave {clave} ya está en uso", "warning")
            return render_template("web_paginas/new.jinja2", form=form, web_rama=web_rama)
        # Guardar
        web_pagina = WebPagina(
            web_rama_id=web_rama.id,
            titulo=safe_string(form.titulo.data, do_unidecode=False, save_enie=True, to_uppercase=False),
            clave=clave,
            fecha_modificacion=date.today(),
            responsable="",
            ruta=form.ruta.data.strip(),
            contenido="",
            estado="BORRADOR",
        )
        web_pagina.save()
        # Guardar bitácora
        bitacora = Bitacora(
            modulo=Modulo.query.filter_by(nombre=MODULO).first(),
            usuario=current_user,
            descripcion=safe_message(f"Nuevo Pagina {web_pagina.clave} en Rama {web_rama.clave}"),
            url=url_for("web_paginas.detail", web_pagina_id=web_pagina.id),
        )
        bitacora.save()
        # Entregar detalle
        flash(bitacora.descripcion, "success")
        return redirect(bitacora.url)
    # Poner valores por defecto
    form.clave.data = web_rama.clave + "-"
    return render_template("web_paginas/new.jinja2", form=form, web_rama=web_rama)


@web_paginas.route("/web_paginas/edicion/<int:web_pagina_id>", methods=["GET", "POST"])
@permission_required(MODULO, Permiso.MODIFICAR)
def edit(web_pagina_id):
    """Editar WebPagina"""
    web_pagina = WebPagina.query.get_or_404(web_pagina_id)
    form = WebPaginaEditForm()
    if form.validate_on_submit():
        es_valido = True
        # Si cambia la clave, validar que la clave no está en uso
        clave = safe_clave(form.clave.data)
        if web_pagina.clave != clave and WebPagina.query.filter_by(clave=clave).filter(WebPagina.id != web_pagina_id).first():
            flash("La clave ya está en uso", "warning")
            es_valido = False
        # Si es válido
        if es_valido:
            # Actualizar
            web_pagina.titulo = safe_string(form.titulo.data, do_unidecode=False, save_enie=True, to_uppercase=False)
            web_pagina.clave = clave
            web_pagina.fecha_modificacion = form.fecha_modificacion.data
            web_pagina.responsable = safe_string(form.responsable.data, save_enie=True, to_uppercase=False)
            web_pagina.ruta = form.ruta.data.strip()
            web_pagina.contenido = form.contenido.data.strip()
            web_pagina.estado = form.estado.data
            web_pagina.tiempo_publicar = form.tiempo_publicar.data
            web_pagina.tiempo_archivar = form.tiempo_archivar.data
            web_pagina.save()
            bitacora = Bitacora(
                modulo=Modulo.query.filter_by(nombre=MODULO).first(),
                usuario=current_user,
                descripcion=safe_message(f"Editado Pagina {web_pagina.clave} en Rama {web_pagina.web_rama.clave}"),
                url=url_for("web_paginas.detail", web_pagina_id=web_pagina.id),
            )
            bitacora.save()
            flash(bitacora.descripcion, "success")
            return redirect(bitacora.url)
    form.titulo.data = web_pagina.titulo
    form.clave.data = web_pagina.clave
    form.fecha_modificacion.data = web_pagina.fecha_modificacion
    form.responsable.data = web_pagina.responsable
    form.ruta.data = web_pagina.ruta
    #form.contenido.data = web_pagina.contenido
    form.estado.data = web_pagina.estado
    form.tiempo_publicar.data = web_pagina.tiempo_publicar
    form.tiempo_archivar.data = web_pagina.tiempo_archivar
    return render_template("web_paginas/edit.jinja2", form=form, web_pagina=web_pagina)


@web_paginas.route("/web_paginas/contenido/<int:web_pagina_id>", methods=["GET", "POST"])
@permission_required(MODULO, Permiso.MODIFICAR)
def content(web_pagina_id):
    """Editar contenido WebPagina"""
    web_pagina = WebPagina.query.get_or_404(web_pagina_id)
    form = WebPaginaContenidoForm()
    if form.validate_on_submit():
        # Actualizar
        web_pagina.contenido = form.contenido.data.strip()
        web_pagina.save()
        bitacora = Bitacora(
            modulo=Modulo.query.filter_by(nombre=MODULO).first(),
            usuario=current_user,
            descripcion=safe_message(f"Editado Contenido de Pagina {web_pagina.clave} en Rama {web_pagina.web_rama.clave}"),
            url=url_for("web_paginas.detail", web_pagina_id=web_pagina.id),
        )
        bitacora.save()
        flash(bitacora.descripcion, "success")
        return redirect(bitacora.url)
        
    form.contenido.data = web_pagina.contenido
    return render_template("web_paginas/content.jinja2", form=form, web_pagina=web_pagina)

@web_paginas.route("/web_paginas/eliminar/<int:web_pagina_id>")
@permission_required(MODULO, Permiso.ADMINISTRAR)
def delete(web_pagina_id):
    """Eliminar WebPagina"""
    web_pagina = WebPagina.query.get_or_404(web_pagina_id)
    if web_pagina.estatus == "A":
        web_pagina.delete()
        bitacora = Bitacora(
            modulo=Modulo.query.filter_by(nombre=MODULO).first(),
            usuario=current_user,
            descripcion=safe_message(f"Eliminado Pagina {web_pagina.clave} en Rama {web_pagina.web_rama.clave}"),
            url=url_for("web_paginas.detail", web_pagina_id=web_pagina.id),
        )
        bitacora.save()
        flash(bitacora.descripcion, "success")
    return redirect(url_for("web_paginas.detail", web_pagina_id=web_pagina.id))


@web_paginas.route("/web_paginas/recuperar/<int:web_pagina_id>")
@permission_required(MODULO, Permiso.ADMINISTRAR)
def recover(web_pagina_id):
    """Recuperar WebPagina"""
    web_pagina = WebPagina.query.get_or_404(web_pagina_id)
    if web_pagina.estatus == "B":
        web_pagina.recover()
        bitacora = Bitacora(
            modulo=Modulo.query.filter_by(nombre=MODULO).first(),
            usuario=current_user,
            descripcion=safe_message(f"Recuperado Pagina {web_pagina.clave} en Rama {web_pagina.web_rama.clave}"),
            url=url_for("web_paginas.detail", web_pagina_id=web_pagina.id),
        )
        bitacora.save()
        flash(bitacora.descripcion, "success")
    return redirect(url_for("web_paginas.detail", web_pagina_id=web_pagina.id))
