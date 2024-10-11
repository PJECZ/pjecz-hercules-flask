"""
Inventarios Equipos, vistas
"""

import json

from flask import Blueprint, flash, redirect, render_template, request, url_for
from flask_login import current_user, login_required
from sqlalchemy import func

from hercules.blueprints.bitacoras.models import Bitacora
from hercules.blueprints.inv_custodias.models import InvCustodia
from hercules.blueprints.inv_equipos.forms import InvEquipoEditForm, InvEquipoNewForm
from hercules.blueprints.inv_equipos.models import InvEquipo
from hercules.blueprints.modulos.models import Modulo
from hercules.blueprints.permisos.models import Permiso
from hercules.blueprints.usuarios.decorators import permission_required
from hercules.extensions import database
from lib.datatables import get_datatable_parameters, output_datatable_json
from lib.safe_string import safe_ip_address, safe_mac_address, safe_message, safe_string

MODULO = "INV EQUIPOS"

inv_equipos = Blueprint("inv_equipos", __name__, template_folder="templates")


@inv_equipos.before_request
@login_required
@permission_required(MODULO, Permiso.VER)
def before_request():
    """Permiso por defecto"""


@inv_equipos.route("/inv_equipos/datatable_json", methods=["GET", "POST"])
def datatable_json():
    """DataTable JSON para listado de InvEquipo"""
    # Tomar parámetros de Datatables
    draw, start, rows_per_page = get_datatable_parameters()
    # Consultar
    consulta = InvEquipo.query
    # Primero filtrar por columnas propias
    if "estatus" in request.form:
        consulta = consulta.filter_by(estatus=request.form["estatus"])
    else:
        consulta = consulta.filter_by(estatus="A")
    if "inv_equipo_id" in request.form:
        try:
            consulta = consulta.filter_by(id=int(request.form["inv_equipo_id"]))
        except ValueError:
            pass
    else:
        if "inv_custodia_id" in request.form:
            consulta = consulta.filter_by(inv_custodia_id=request.form["inv_custodia_id"])
        if "inv_modelo_id" in request.form:
            consulta = consulta.filter_by(inv_modelo_id=request.form["inv_modelo_id"])
        if "inv_red_id" in request.form:
            consulta = consulta.filter_by(inv_red_id=request.form["inv_red_id"])
        if "estado" in request.form:
            estado = safe_string(request.form["estado"])
            if estado != "":
                consulta = consulta.filter_by(estado=estado)
        if "numero_serie" in request.form:
            numero_serie = safe_string(request.form["numero_serie"])
            if numero_serie != "":
                consulta = consulta.filter(InvEquipo.numero_serie.contains(numero_serie))
        if "numero_inventario" in request.form:
            numero_inventario = safe_string(request.form["numero_inventario"])
            if numero_inventario != "":
                consulta = consulta.filter(InvEquipo.numero_inventario.contains(numero_inventario))
        if "descripcion" in request.form:
            descripcion = safe_string(request.form["descripcion"])
            if descripcion != "":
                consulta = consulta.filter(InvEquipo.descripcion.contains(descripcion))
        if "tipo" in request.form:
            tipo = safe_string(request.form["tipo"])
            if tipo != "":
                consulta = consulta.filter(InvEquipo.tipo == tipo)
        if "direccion_ip" in request.form:
            direccion_ip = safe_string(request.form["direccion_ip"])
            if direccion_ip != "":
                consulta = consulta.filter(InvEquipo.direccion_ip.contains(direccion_ip))
        if "direccion_mac" in request.form:
            direccion_mac = safe_string(request.form["direccion_mac"])
            if direccion_mac != "":
                consulta = consulta.filter(InvEquipo.direccion_mac.contains(direccion_mac))
    # Ordenar y paginar
    registros = consulta.order_by(InvEquipo.id).offset(start).limit(rows_per_page).all()
    total = consulta.count()
    # Elaborar datos para DataTable
    data = []
    for resultado in registros:
        data.append(
            {
                "detalle": {
                    "id": resultado.id,
                    "url": url_for("inv_equipos.detail", inv_equipo_id=resultado.id),
                },
                "tipo": resultado.tipo,
                "inv_marca_nombre": resultado.inv_modelo.inv_marca.nombre,
                "descripcion": resultado.descripcion,
                "fecha_fabricacion_anio": resultado.fecha_fabricacion_anio,
                "direccion_ip": resultado.direccion_ip,
                "direccion_mac": resultado.direccion_mac,
                "numero_serie": resultado.numero_serie,
                "numero_inventario": resultado.numero_inventario,
                "inv_modelo_descripcion": resultado.inv_modelo.descripcion,
                "inv_red_nombre": resultado.inv_red.nombre,
                "inv_custodia_nombre_completo": resultado.inv_custodia.nombre_completo,
                "estado": resultado.estado,
            }
        )
    # Entregar JSON
    return output_datatable_json(draw, total, data)


@inv_equipos.route("/inv_equipos")
def list_active():
    """Listado de InvEquipo activos"""
    return render_template(
        "inv_equipos/list.jinja2",
        filtros=json.dumps({"estatus": "A"}),
        titulo="Equipos",
        estatus="A",
    )


@inv_equipos.route("/inv_equipos/inactivos")
@permission_required(MODULO, Permiso.ADMINISTRAR)
def list_inactive():
    """Listado de InvEquipo inactivos"""
    return render_template(
        "inv_equipos/list.jinja2",
        filtros=json.dumps({"estatus": "B"}),
        titulo="Equipos inactivos",
        estatus="B",
    )


@inv_equipos.route("/inv_equipos/estado/<string:estado>")
@permission_required(MODULO, Permiso.VER)
def list_by_estado(estado):
    """Listado de InvEquipo por estado"""
    return render_template(
        "inv_equipos/list.jinja2",
        filtros=json.dumps({"estatus": "A", "estado": estado}),
        titulo=f"Equipos en estado '{estado}'",
        estatus="A",
    )


@inv_equipos.route("/inv_equipos/tipo/<string:tipo>")
@permission_required(MODULO, Permiso.MODIFICAR)
def list_by_tipo(tipo):
    """Listado de InvEquipo por tipo"""
    return render_template(
        "inv_equipos/list.jinja2",
        filtros=json.dumps({"estatus": "A", "tipo": tipo}),
        titulo=f"Equipos tipo '{tipo}'",
        estatus="A",
    )


@inv_equipos.route("/inv_equipos/<int:inv_equipo_id>")
def detail(inv_equipo_id):
    """Detalle de un InvEquipo"""
    inv_equipo = InvEquipo.query.get_or_404(inv_equipo_id)
    return render_template("inv_equipos/detail.jinja2", inv_equipo=inv_equipo)


@inv_equipos.route("/inv_equipos/nuevo/<int:inv_custodia_id>", methods=["GET", "POST"])
@permission_required(MODULO, Permiso.CREAR)
def new_with_inv_custodia_id(inv_custodia_id):
    """Nuevo InvEquipo"""
    inv_custodia = InvCustodia.query.get_or_404(inv_custodia_id)
    form = InvEquipoNewForm()
    if form.validate_on_submit():
        # Guardar
        inv_equipo = InvEquipo(
            inv_custodia_id=inv_custodia.id,
            inv_modelo_id=form.inv_modelo.data,
            descripcion=safe_string(form.descripcion.data, save_enie=True),
            tipo=form.tipo.data,
            fecha_fabricacion_anio=form.fecha_fabricacion_anio.data,
            numero_serie=safe_string(form.numero_serie.data),
            numero_inventario=form.numero_inventario.data,
            inv_red_id=form.inv_red.data,
            direccion_ip=safe_ip_address(form.direccion_ip.data),
            direccion_mac=safe_mac_address(form.direccion_mac.data),
            numero_nodo=form.numero_nodo.data,
            numero_switch=form.numero_switch.data,
            numero_puerto=form.numero_puerto.data,
            estado=form.estado.data,
        )
        inv_equipo.save()
        # Guardar bitácora
        bitacora = Bitacora(
            modulo=Modulo.query.filter_by(nombre=MODULO).first(),
            usuario=current_user,
            descripcion=safe_message(f"Nuevo InvEquipo {inv_equipo.id} {inv_equipo.descripcion}"),
            url=url_for("inv_equipos.detail", inv_equipo_id=inv_equipo.id),
        )
        bitacora.save()
        # Entregar detalle
        flash(bitacora.descripcion, "success")
        return redirect(bitacora.url)
    return render_template("inv_equipos/new.jinja2", form=form, inv_custodia=inv_custodia)


@inv_equipos.route("/inv_equipos/edicion/<int:inv_equipo_id>", methods=["GET", "POST"])
@permission_required(MODULO, Permiso.MODIFICAR)
def edit(inv_equipo_id):
    """Editar InvEquipo"""
    inv_equipo = InvEquipo.query.get_or_404(inv_equipo_id)
    form = InvEquipoEditForm()
    if form.validate_on_submit():
        # Es opcional cambiar el inv_modelo
        if form.inv_modelo.data and form.inv_modelo.data != inv_equipo.inv_modelo_id:
            inv_equipo.inv_modelo_id = form.inv_modelo.data
        # Guardar
        inv_equipo.descripcion = safe_string(form.descripcion.data, save_enie=True)
        inv_equipo.tipo = form.tipo.data
        inv_equipo.fecha_fabricacion_anio = form.fecha_fabricacion_anio.data
        inv_equipo.numero_serie = safe_string(form.numero_serie.data)
        inv_equipo.numero_inventario = form.numero_inventario.data
        inv_equipo.inv_red_id = form.inv_red.data
        inv_equipo.direccion_ip = safe_ip_address(form.direccion_ip.data)
        inv_equipo.direccion_mac = safe_mac_address(form.direccion_mac.data)
        inv_equipo.numero_nodo = form.numero_nodo.data
        inv_equipo.numero_switch = form.numero_switch.data
        inv_equipo.numero_puerto = form.numero_puerto.data
        inv_equipo.estado = form.estado.data
        inv_equipo.save()
        # Guardar bitácora
        bitacora = Bitacora(
            modulo=Modulo.query.filter_by(nombre=MODULO).first(),
            usuario=current_user,
            descripcion=safe_message(f"Editado InvEquipo {inv_equipo.id} {inv_equipo.descripcion}"),
            url=url_for("inv_equipos.detail", inv_equipo_id=inv_equipo.id),
        )
        bitacora.save()
        # Entregar detalle
        flash(bitacora.descripcion, "success")
        return redirect(bitacora.url)
    form.inv_modelo.data = inv_equipo.inv_modelo_id
    form.descripcion.data = inv_equipo.descripcion
    form.tipo.data = inv_equipo.tipo
    form.fecha_fabricacion_anio.data = inv_equipo.fecha_fabricacion_anio
    form.numero_serie.data = inv_equipo.numero_serie
    form.numero_inventario.data = inv_equipo.numero_inventario
    form.inv_red.data = inv_equipo.inv_red_id
    form.direccion_ip.data = inv_equipo.direccion_ip
    form.direccion_mac.data = inv_equipo.direccion_mac
    form.numero_nodo.data = inv_equipo.numero_nodo
    form.numero_switch.data = inv_equipo.numero_switch
    form.numero_puerto.data = inv_equipo.numero_puerto
    form.estado.data = inv_equipo.estado
    return render_template("inv_equipos/edit.jinja2", form=form, inv_equipo=inv_equipo)


@inv_equipos.route("/inv_equipos/eliminar/<int:inv_equipo_id>")
@permission_required(MODULO, Permiso.ADMINISTRAR)
def delete(inv_equipo_id):
    """Eliminar InvEquipo"""
    inv_equipo = InvEquipo.query.get_or_404(inv_equipo_id)
    if inv_equipo.estatus == "A":
        # Eliminar InvEquipo
        inv_equipo.delete()
        # Eliminar los InvComponentes de cada InvEquipo
        for inv_componente in inv_equipo.inv_componentes:
            inv_componente.delete()
        # Agregar a la bitácora
        bitacora = Bitacora(
            modulo=Modulo.query.filter_by(nombre=MODULO).first(),
            usuario=current_user,
            descripcion=safe_message(f"Eliminado InvEquipo {inv_equipo.id}"),
            url=url_for("inv_equipos.detail", inv_equipo_id=inv_equipo.id),
        )
        bitacora.save()
        flash(bitacora.descripcion, "success")
    return redirect(url_for("inv_equipos.detail", inv_equipo_id=inv_equipo.id))


@inv_equipos.route("/inv_equipos/recuperar/<int:inv_equipo_id>")
@permission_required(MODULO, Permiso.ADMINISTRAR)
def recover(inv_equipo_id):
    """Recuperar InvEquipo"""
    inv_equipo = InvEquipo.query.get_or_404(inv_equipo_id)
    if inv_equipo.estatus == "B":
        # Recuperar InvEquipo
        inv_equipo.recover()
        # Recuperar los InvComponentes de cada InvEquipo
        for inv_componente in inv_equipo.inv_componentes:
            inv_componente.recover()
        # Agregar a la bitácora
        bitacora = Bitacora(
            modulo=Modulo.query.filter_by(nombre=MODULO).first(),
            usuario=current_user,
            descripcion=safe_message(f"Recuperado InvEquipo {inv_equipo.id}"),
            url=url_for("inv_equipos.detail", inv_equipo_id=inv_equipo.id),
        )
        bitacora.save()
        flash(bitacora.descripcion, "success")
    return redirect(url_for("inv_equipos.detail", inv_equipo_id=inv_equipo.id))


@inv_equipos.route("/inv_equipos/tablero")
@permission_required(MODULO, Permiso.MODIFICAR)
def dashboard():
    """Tablero de InvEquipo"""

    # Cantidades de equipos por tipo
    inv_equipos_cantidades_por_tipo = (
        database.session.query(InvEquipo.tipo, func.count(InvEquipo.id))
        .where(InvEquipo.estatus == "A")
        .group_by(InvEquipo.tipo)
        .order_by(InvEquipo.tipo)
        .all()
    )

    # Cantidades de equipos por tipo y año de fabricación
    inv_equipos_cantidades_por_tipo_y_fabricacion_anio = (
        database.session.query(InvEquipo.fecha_fabricacion_anio, InvEquipo.tipo, func.count(InvEquipo.id))
        .where(InvEquipo.fecha_fabricacion_anio.isnot(None))
        .where(InvEquipo.estatus == "A")
        .group_by(InvEquipo.fecha_fabricacion_anio, InvEquipo.tipo)
        .all()
    )

    # Estructurar para hacer una tabla con Jinja2 con los años en renglones y los tipos en columnas
    inv_equipos_matriz_tipos_anios = {}
    for fabricacion_anio, tipo, cantidad in inv_equipos_cantidades_por_tipo_y_fabricacion_anio:
        if fabricacion_anio not in inv_equipos_matriz_tipos_anios:
            inv_equipos_matriz_tipos_anios[fabricacion_anio] = {}
        inv_equipos_matriz_tipos_anios[fabricacion_anio][tipo] = cantidad

    # Entregar
    return render_template(
        "inv_equipos/dashboard.jinja2",
        inv_equipos_cantidades_por_tipo=inv_equipos_cantidades_por_tipo,
        inv_equipos_matriz_tipos_anios=inv_equipos_matriz_tipos_anios,
    )


@inv_equipos.route("/inv_equipos/exportar_reporte_xlsx/<string:tipo>")
@permission_required(MODULO, Permiso.MODIFICAR)
def exportar_reporte_xlsx(tipo):
    """Lanzar tarea en el fondo para exportar"""
    tarea = current_user.launch_task(
        comando="inv_equipos.tasks.lanzar_exportar_reporte_xlsx",
        mensaje="Exportando el reporte de equipos a un archivo XLSX...",
        tipo=tipo,
    )
    flash("Se ha lanzado esta tarea en el fondo. Esta página se va a recargar en 10 segundos...", "info")
    return redirect(url_for("tareas.detail", tarea_id=tarea.id))
