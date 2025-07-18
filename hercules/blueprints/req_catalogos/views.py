"""
Requisiciones Catálogos, vistas
"""

import json
from flask import Blueprint, flash, redirect, render_template, request, url_for
from flask_login import current_user, login_required

from lib.datatables import get_datatable_parameters, output_datatable_json
from lib.safe_string import safe_string, safe_message

from hercules.blueprints.bitacoras.models import Bitacora
from hercules.blueprints.modulos.models import Modulo
from hercules.blueprints.permisos.models import Permiso
from hercules.blueprints.usuarios.decorators import permission_required
from hercules.blueprints.req_catalogos.models import ReqCatalogo
from hercules.blueprints.req_catalogos.forms import ReqCatalogoNewForm
from hercules.blueprints.req_categorias.models import ReqCategoria

MODULO = "REQ CATALOGOS"

# Roles que deben estar en la base de datos
ROL_ASISTENTES = "REQUISICIONES ASISTENTES"
ROL_SOLICITANTES = "REQUISICIONES SOLICITANTES"
ROL_AUTORIZANTES = "REQUISICIONES AUTORIZANTES"
ROL_REVISANTES = "REQUISICIONES REVISANTES"

ROLES_PUEDEN_VER = (ROL_SOLICITANTES, ROL_AUTORIZANTES, ROL_REVISANTES, ROL_ASISTENTES)
ROLES_PUEDEN_IMPRIMIR = (ROL_SOLICITANTES, ROL_AUTORIZANTES, ROL_REVISANTES, ROL_ASISTENTES)

req_catalogos = Blueprint("req_catalogos", __name__, template_folder="templates")


@req_catalogos.before_request
@login_required
@permission_required(MODULO, Permiso.VER)
def before_request():
    """Permiso por defecto"""


@req_catalogos.route("/req_catalogos/datatable_json", methods=["GET", "POST"])
def datatable_json():
    """DataTable JSON para listado de Catalogo"""
    # Tomar parámetros de Datatables
    draw, start, rows_per_page = get_datatable_parameters()
    # Consultar
    consulta = ReqCatalogo.query
    if "estatus" in request.form:
        consulta = consulta.filter_by(estatus=request.form["estatus"])
    else:
        consulta = consulta.filter_by(estatus="A")
    if "clave" in request.form:
        consulta = consulta.filter(ReqCatalogo.clave.contains(safe_string(request.form["clave"], to_uppercase=False)))
    if "descripcion" in request.form:
        consulta = consulta.filter(ReqCatalogo.descripcion.contains(safe_string(request.form["descripcion"], to_uppercase=True)))
    registros = consulta.order_by(ReqCatalogo.id).offset(start).limit(rows_per_page).all()

    total = consulta.count()
    # Elaborar datos para DataTable
    data = []
    for resultado in registros:
        print(resultado)
        data.append(
            {
                "id": resultado.id,
                "clave": resultado.clave,
                "descripcion": resultado.descripcion,
                "unidad": resultado.unidad_medida,
                "categoria": resultado.req_categoria_id,
                "detalle": {
                    "clave": resultado.clave,
                    "url": url_for("req_catalogos.detail", req_catalogo_id=resultado.id),
                },
            }
        )
    # Entregar JSON
    return output_datatable_json(draw, total, data)


@req_catalogos.route("/req_catalogos/nuevo", methods=["GET", "POST"])
@permission_required(MODULO, Permiso.CREAR)
def new():
    """Catalogos nuevo registro"""
    form = ReqCatalogoNewForm()
    form.categoria.choices = [("", "")] + [(c.id, c.descripcion) for c in ReqCategoria.query.order_by("descripcion")]
    form.unidad.choices = (
        [("", "")]
        + [("M", "Metros")]
        + [("KG", "Kilogramos")]
        + [("GRS", "Gramos")]
        + [("PIEZA", "Pieza")]
        + [("LTS", "Litros")]
    )
    if form.validate_on_submit():
        # Guardar articulo
        req_catalogo = ReqCatalogo(
            clave=safe_string(form.clave.data, max_len=6, to_uppercase=True, save_enie=True),
            descripcion=safe_string(form.descripcion.data, max_len=256, to_uppercase=True, save_enie=True),
            unidad_medida=safe_string(form.unidad.data, to_uppercase=True, save_enie=True),
            req_categoria_id=safe_string(form.categoria.data, to_uppercase=True, save_enie=True),
        )
        req_catalogo.save()

        # Guardar en la bitacora
        bitacora = Bitacora(
            modulo=Modulo.query.filter_by(nombre=MODULO).first(),
            usuario=current_user,
            descripcion=safe_message(f"Articulo creado {req_catalogo.descripcion}"),
            url=url_for("req_catalogos.detail", req_catalogo_id=req_catalogo.id),
        )
        bitacora.save()
        flash(bitacora.descripcion, "success")
        return redirect(bitacora.url)
    return render_template("req_catalogos/new.jinja2", titulo="Registro nuevo de Catalogo", form=form)


@req_catalogos.route("/req_catalogos/<int:req_catalogo_id>")
def detail(req_catalogo_id):
    """Detalle de un registro del Catalogo"""
    req_catalogo = ReqCatalogo.query.get_or_404(req_catalogo_id)
    #    articulos = db.session.query(ReqRequisicionRegistro, ReqCatalogo).filter_by(req_requisicion_id=req_requisicion_id).join(ReqCatalogo).all()
    return render_template("req_catalogos/detail.jinja2", req_catalogo=req_catalogo)


@req_catalogos.route("/req_catalogos")
def list_active():
    """Listado de Catalogos activos"""
    return render_template(
        "req_catalogos/list.jinja2",
        filtros=json.dumps({"estatus": "A"}),
        titulo="Catalogos",
        estatus="A",
    )


@req_catalogos.route("/req_catalogos/inactivos")
@permission_required(MODULO, Permiso.MODIFICAR)
def list_inactive():
    """Listado de registro de Catalogo inactivos"""
    return render_template(
        "req_catalogos/list.jinja2",
        filtros=json.dumps({"estatus": "B"}),
        titulo="Listado de registros de Catalogo inactivos",
        estatus="B",
    )
