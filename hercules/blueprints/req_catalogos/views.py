"""
Requisiciones Catálogos, vistas
"""

import json
from flask import Blueprint, flash, redirect, render_template, request, url_for
from flask_login import current_user, login_required

from lib.datatables import get_datatable_parameters, output_datatable_json
from lib.safe_string import safe_string, safe_message, safe_clave

from hercules.blueprints.bitacoras.models import Bitacora
from hercules.blueprints.modulos.models import Modulo
from hercules.blueprints.permisos.models import Permiso
from hercules.blueprints.usuarios.decorators import permission_required
from hercules.blueprints.req_catalogos.models import ReqCatalogo
from hercules.blueprints.req_catalogos.forms import ReqCatalogoForm, ReqCatalogoWithCategoriaForm
from hercules.blueprints.req_categorias.models import ReqCategoria


MODULO = "REQ CATALOGOS"

req_catalogos = Blueprint("req_catalogos", __name__, template_folder="templates")


@req_catalogos.before_request
@login_required
@permission_required(MODULO, Permiso.VER)
def before_request():
    """Permiso por defecto"""


@req_catalogos.route("/req_catalogos/datatable_json", methods=["GET", "POST"])
def datatable_json():
    """DataTable JSON para listado de Req Catalogos"""
    # Tomar parámetros de Datatables
    draw, start, rows_per_page = get_datatable_parameters()
    # Consultar
    consulta = ReqCatalogo.query
    # Primero filtrar por columnas propias
    if "estatus" in request.form:
        consulta = consulta.filter(ReqCatalogo.estatus == request.form["estatus"])
    else:
        consulta = consulta.filter(ReqCatalogo.estatus == "A")
    if "clave" in request.form:
        clave = safe_clave(request.form["clave"])
        if clave:
            consulta = consulta.filter(ReqCatalogo.clave.contains(clave))
    if "descripcion" in request.form:
        descripcion = safe_string(request.form["descripcion"])
        if descripcion:
            consulta = consulta.filter(ReqCatalogo.descripcion.contains(descripcion))
    if "req_categoria_id" in request.form:
        consulta = consulta.filter(ReqCatalogo.req_categoria_id == request.form["req_categoria_id"])
    # Luego filtrar por columnas de otras tablas
    # if "persona_rfc" in request.form:
    #     consulta = consulta.join(Persona)
    #     consulta = consulta.filter(Persona.rfc.contains(safe_rfc(request.form["persona_rfc"], search_fragment=True)))
    # Ordenar y paginar
    registros = consulta.order_by(ReqCatalogo.clave).offset(start).limit(rows_per_page).all()
    total = consulta.count()
    # Elaborar datos para DataTable
    data = []
    for resultado in registros:
        data.append(
            {
                "detalle": {
                    "clave": resultado.clave,
                    "url": url_for("req_catalogos.detail", req_catalogo_id=resultado.id),
                },
                "descripcion": resultado.descripcion,
                "req_categoria": {
                    "nombre": resultado.req_categoria.clave_descripcion,
                    "url": url_for("req_categorias.detail", req_categoria_id=resultado.req_categoria.id),
                },
                "unidad_medida": resultado.unidad_medida_descripcion,
            }
        )
    # Entregar JSON
    return output_datatable_json(draw, total, data)


@req_catalogos.route("/req_catalogos")
def list_active():
    """Listado de Req Catalogos activos"""
    return render_template(
        "req_catalogos/list.jinja2",
        filtros=json.dumps({"estatus": "A"}),
        titulo="Requisiciones Catálogos",
        estatus="A",
    )


@req_catalogos.route("/req_catalogos/inactivos")
@permission_required(MODULO, Permiso.ADMINISTRAR)
def list_inactive():
    """Listado de Req Catalogos inactivos"""
    return render_template(
        "req_catalogos/list.jinja2",
        filtros=json.dumps({"estatus": "B"}),
        titulo="Requisiciones Catálogos inactivos",
        estatus="B",
    )


@req_catalogos.route("/req_catalogos/<int:req_catalogo_id>")
def detail(req_catalogo_id):
    """Detalle de un Req Catalogo"""
    req_catalogo = ReqCatalogo.query.get_or_404(req_catalogo_id)
    return render_template("req_catalogos/detail.jinja2", req_catalogo=req_catalogo)


@req_catalogos.route("/req_catalogos/nuevo", methods=["GET", "POST"])
@permission_required(MODULO, Permiso.CREAR)
def new():
    """Nuevo Req Catalogo"""
    form = ReqCatalogoForm()
    if form.validate_on_submit():
        es_valido = True
        # Validar que no se repita la clave
        clave = safe_clave(form.clave.data)
        clave_repetida = ReqCatalogo.query.filter_by(clave=clave).first()
        if clave_repetida:
            flash(f"La clave '{clave_repetida}' ya existe", "warning")
            es_valido = False
        if es_valido:
            req_catalogo = ReqCatalogo(
                clave=clave,
                descripcion=safe_string(form.descripcion.data),
                unidad_medida=form.unidad_medida.data,
                req_categoria_id=form.categoria.data,
            )
            req_catalogo.save()
            bitacora = Bitacora(
                modulo=Modulo.query.filter_by(nombre=MODULO).first(),
                usuario=current_user,
                descripcion=safe_message(f"Nuevo Req Catalogo {req_catalogo.clave}"),
                url=url_for("req_catalogos.detail", req_catalogo_id=req_catalogo.id),
            )
            bitacora.save()
            flash(bitacora.descripcion, "success")
            return redirect(bitacora.url)
    # Entrega
    return render_template("req_catalogos/new.jinja2", form=form)


@req_catalogos.route("/req_catalogos/nuevo_con_categoria/<int:req_categoria_id>", methods=["GET", "POST"])
@permission_required(MODULO, Permiso.CREAR)
def new_with_categoria(req_categoria_id):
    """Nuevo Req Catalogo"""
    req_categoria = ReqCategoria.query.get_or_404(req_categoria_id)
    form = ReqCatalogoWithCategoriaForm()
    if form.validate_on_submit():
        es_valido = True
        # Validar que no se repita la clave
        clave = safe_clave(form.clave.data)
        clave_repetida = ReqCatalogo.query.filter_by(clave=clave).first()
        if clave_repetida:
            flash(f"La clave '{clave_repetida}' ya existe", "warning")
            es_valido = False
        if es_valido:
            req_catalogo = ReqCatalogo(
                clave=clave,
                descripcion=safe_string(form.descripcion.data),
                unidad_medida=form.unidad_medida.data,
                req_categoria=req_categoria,
            )
            req_catalogo.save()
            bitacora = Bitacora(
                modulo=Modulo.query.filter_by(nombre=MODULO).first(),
                usuario=current_user,
                descripcion=safe_message(f"Nuevo Req Catalogo {req_catalogo.clave}"),
                url=url_for("req_catalogos.detail", req_catalogo_id=req_catalogo.id),
            )
            bitacora.save()
            flash(bitacora.descripcion, "success")
            return redirect(bitacora.url)
    # Cargar datos en el formulario
    form.categoria.data = req_categoria.clave_descripcion
    # Entrega
    return render_template("req_catalogos/new_with_categoria.jinja2", form=form, req_categoria=req_categoria)


@req_catalogos.route("/req_catalogos/edicion/<int:req_catalogo_id>", methods=["GET", "POST"])
@permission_required(MODULO, Permiso.MODIFICAR)
def edit(req_catalogo_id):
    """Editar Req Catálogo"""
    req_catalogo = ReqCatalogo.query.get_or_404(req_catalogo_id)
    form = ReqCatalogoForm()
    if form.validate_on_submit():
        es_valido = True
        # Validar que no se repita la clave
        clave = safe_clave(form.clave.data)
        clave_repetida = ReqCatalogo.query.filter_by(clave=clave).filter(ReqCatalogo.id != req_catalogo_id).first()
        if clave_repetida:
            flash(f"La clave '{clave}' ya está en uso.", "warning")
            es_valido = False
        if es_valido:
            req_catalogo.clave = clave
            req_catalogo.descripcion = safe_string(form.descripcion.data)
            req_catalogo.req_categoria_id = form.categoria.data
            req_catalogo.unidad_medida = form.unidad_medida.data
            req_catalogo.save()
            bitacora = Bitacora(
                modulo=Modulo.query.filter_by(nombre=MODULO).first(),
                usuario=current_user,
                descripcion=safe_message(f"Editado Req Catálogo {req_catalogo.clave}"),
                url=url_for("req_catalogos.detail", req_catalogo_id=req_catalogo.id),
            )
            bitacora.save()
            flash(bitacora.descripcion, "success")
            return redirect(bitacora.url)
    # Cargar datos al formulario
    form.clave.data = req_catalogo.clave
    form.descripcion.data = req_catalogo.descripcion
    form.categoria.data = req_catalogo.req_categoria.id
    form.unidad_medida.data = req_catalogo.unidad_medida
    # Entregar
    return render_template("req_catalogos/edit.jinja2", form=form, req_catalogo=req_catalogo)


@req_catalogos.route("/req_catalogos/eliminar/<int:req_catalogo_id>")
@permission_required(MODULO, Permiso.ADMINISTRAR)
def delete(req_catalogo_id):
    """Eliminar Req Catálogo"""
    req_catalogo = ReqCatalogo.query.get_or_404(req_catalogo_id)
    if req_catalogo.estatus == "A":
        req_catalogo.delete()
        bitacora = Bitacora(
            modulo=Modulo.query.filter_by(nombre=MODULO).first(),
            usuario=current_user,
            descripcion=safe_message(f"Eliminado Req Catálogo {req_catalogo.clave}"),
            url=url_for("req_catalogos.detail", req_catalogo_id=req_catalogo.id),
        )
        bitacora.save()
        flash(bitacora.descripcion, "success")
    return redirect(url_for("req_catalogos.detail", req_catalogo_id=req_catalogo.id))


@req_catalogos.route("/req_catalogos/recuperar/<int:req_catalogo_id>")
@permission_required(MODULO, Permiso.ADMINISTRAR)
def recover(req_catalogo_id):
    """Recuperar Req Catálogo"""
    req_catalogo = ReqCatalogo.query.get_or_404(req_catalogo_id)
    if req_catalogo.estatus == "B":
        req_catalogo.recover()
        bitacora = Bitacora(
            modulo=Modulo.query.filter_by(nombre=MODULO).first(),
            usuario=current_user,
            descripcion=safe_message(f"Recuperado Req Catálogo {req_catalogo.clave}"),
            url=url_for("req_catalogos.detail", req_catalogo_id=req_catalogo.id),
        )
        bitacora.save()
        flash(bitacora.descripcion, "success")
    return redirect(url_for("req_catalogos.detail", req_catalogo_id=req_catalogo.id))
