"""
Inventarios Custodias, vistas
"""

import json
from datetime import date

from flask import Blueprint, flash, redirect, render_template, request, url_for
from flask_login import current_user, login_required
from sqlalchemy import func

from hercules.blueprints.bitacoras.models import Bitacora
from hercules.blueprints.domicilios.models import Domicilio
from hercules.blueprints.inv_custodias.forms import InvCustodiaForm
from hercules.blueprints.inv_custodias.models import InvCustodia
from hercules.blueprints.inv_equipos.models import InvEquipo
from hercules.blueprints.modulos.models import Modulo
from hercules.blueprints.oficinas.models import Oficina
from hercules.blueprints.permisos.models import Permiso
from hercules.blueprints.usuarios.decorators import permission_required
from hercules.blueprints.usuarios.models import Usuario
from hercules.extensions import database
from lib.datatables import get_datatable_parameters, output_datatable_json
from lib.safe_string import safe_message, safe_string

MODULO = "INV CUSTODIAS"

inv_custodias = Blueprint("inv_custodias", __name__, template_folder="templates")


@inv_custodias.before_request
@login_required
@permission_required(MODULO, Permiso.VER)
def before_request():
    """Permiso por defecto"""


@inv_custodias.route("/inv_custodias/datatable_json", methods=["GET", "POST"])
def datatable_json():
    """DataTable JSON para listado de InvCustodia"""
    # Tomar parámetros de Datatables
    draw, start, rows_per_page = get_datatable_parameters()
    # En move_1_choose_custodia, se puede especificar el origen_inv_custodia_id
    origen_inv_custodia_id = None
    if "origen_inv_custodia_id" in request.form:
        origen_inv_custodia_id = int(request.form["origen_inv_custodia_id"])
    # Consultar
    consulta = InvCustodia.query
    # Primero filtrar por columnas propias
    if "estatus" in request.form:
        consulta = consulta.filter(InvCustodia.estatus == request.form["estatus"])
    else:
        consulta = consulta.filter(InvCustodia.estatus == "A")
    if "inv_custodia_id" in request.form:
        try:
            consulta = consulta.filter(InvCustodia.id == int(request.form["inv_custodia_id"]))
        except ValueError:
            pass
    else:
        if "usuario_id" in request.form:
            consulta = consulta.filter(InvCustodia.usuario_id == request.form["usuario_id"])
        if "nombre_completo" in request.form:
            nombre_completo = safe_string(request.form["nombre_completo"])
            if nombre_completo != "":
                consulta = consulta.filter(InvCustodia.nombre_completo.contains(nombre_completo))
        if "domicilio_id" in request.form:
            consulta = consulta.join(Usuario).join(Oficina).join(Domicilio).filter(Domicilio.id == request.form["domicilio_id"])
    # Ordenar y paginar
    registros = consulta.order_by(InvCustodia.id).offset(start).limit(rows_per_page).all()
    total = consulta.count()
    # Elaborar datos para DataTable
    data = []
    for resultado in registros:
        data.append(
            {
                "detalle": {
                    "id": resultado.id,
                    "url": url_for("inv_custodias.detail", inv_custodia_id=resultado.id),
                },
                "move_inv_equipo": {
                    "id": resultado.id,
                    "url": (
                        url_for(
                            "inv_custodias.move_2_choose_equipos",
                            origen_inv_custodia_id=origen_inv_custodia_id,
                            destino_inv_custodia_id=resultado.id,
                        )
                        if origen_inv_custodia_id
                        else ""
                    ),
                },
                "nombre_completo": resultado.nombre_completo,
                "oficina_clave": resultado.usuario.oficina.clave,
                "fecha": resultado.fecha.strftime("%Y-%m-%d"),
                "equipos_cantidad": resultado.equipos_cantidad if resultado.equipos_cantidad != 0 else "-",
                "equipos_fotos_cantidad": resultado.equipos_fotos_cantidad if resultado.equipos_fotos_cantidad != 0 else "-",
            }
        )
    # Entregar JSON
    return output_datatable_json(draw, total, data)


@inv_custodias.route("/inv_custodias")
def list_active():
    """Listado de InvCustodia activos"""

    # Definir filtros por defecto
    filtros = {"estatus": "A"}
    titulo = "Custodias"

    # Si viene usuario_id en la URL, agregar a los filtros
    try:
        usuario_id = int(request.args.get("usuario_id"))
        usuario = Usuario.query.get_or_404(usuario_id)
        filtros = {"estatus": "A", "usuario_id": usuario_id}
        titulo = f"Custodias de {usuario.nombre}"
    except (TypeError, ValueError):
        pass

    # Entregar
    return render_template(
        "inv_custodias/list.jinja2",
        filtros=json.dumps(filtros),
        titulo=titulo,
        estatus="A",
    )


@inv_custodias.route("/inv_custodias/inactivos")
@permission_required(MODULO, Permiso.ADMINISTRAR)
def list_inactive():
    """Listado de InvCustodia inactivos"""
    return render_template(
        "inv_custodias/list.jinja2",
        filtros=json.dumps({"estatus": "B"}),
        titulo="Custodias inactivas",
        estatus="B",
    )


@inv_custodias.route("/inv_custodias/domicilio/<int:domicilio_id>")
@permission_required(MODULO, Permiso.VER)
def list_by_domicilio_id(domicilio_id):
    """Listado de InvCustodia por domicilio_id"""
    domicilio = Domicilio.query.get_or_404(domicilio_id)
    return render_template(
        "inv_custodias/list.jinja2",
        filtros=json.dumps({"estatus": "A", "domicilio_id": domicilio_id}),
        titulo=f"Custodias en el edificio '{domicilio.edificio}'",
        estatus="A",
    )


@inv_custodias.route("/inv_custodias/<int:inv_custodia_id>")
def detail(inv_custodia_id):
    """Detalle de un InvCustodia"""
    inv_custodia = InvCustodia.query.get_or_404(inv_custodia_id)
    return render_template("inv_custodias/detail.jinja2", inv_custodia=inv_custodia)


@inv_custodias.route("/inv_custodias/move_1_choose_custodia/<int:origen_inv_custodia_id>")
@permission_required(MODULO, Permiso.MODIFICAR)
def move_1_choose_custodia(origen_inv_custodia_id):
    """Mover Equipos 1. Elegir Custodia de destino"""
    origen_inv_custodia = InvCustodia.query.get_or_404(origen_inv_custodia_id)
    return render_template(
        "inv_custodias/move_1_choose_inv_custodia.jinja2",
        origen_inv_custodia=origen_inv_custodia,
    )


@inv_custodias.route("/inv_custodias/move_2_choose_equipos/<int:origen_inv_custodia_id>/<int:destino_inv_custodia_id>")
@permission_required(MODULO, Permiso.MODIFICAR)
def move_2_choose_equipos(origen_inv_custodia_id, destino_inv_custodia_id):
    """Mover Equipos 2. Elegir Equipos"""
    if origen_inv_custodia_id == destino_inv_custodia_id:
        flash("No se puede mover equipos a la misma custodia", "warning")
        return redirect(url_for("inv_custodias.move_1_choose_custodia", origen_inv_custodia_id=origen_inv_custodia_id))
    origen_inv_custodia = InvCustodia.query.get_or_404(origen_inv_custodia_id)
    destino_inv_custodia = InvCustodia.query.get_or_404(destino_inv_custodia_id)
    return render_template(
        "inv_custodias/move_2_move_inv_equipo.jinja2",
        origen_inv_custodia=origen_inv_custodia,
        destino_inv_custodia=destino_inv_custodia,
    )


@inv_custodias.route(
    "/inv_custodias/move_3_move_equipo/<int:origen_inv_custodia_id>/<int:destino_inv_custodia_id>", methods=["POST"]
)
@permission_required(MODULO, Permiso.MODIFICAR)
def move_3_move_equipo(origen_inv_custodia_id, destino_inv_custodia_id):
    """Mover Equipos 3. Mover Equipos"""
    # Validar que sean diferentes las custodias
    if origen_inv_custodia_id == destino_inv_custodia_id:
        return {
            "success": False,
            "message": "No se puede mover equipos a la misma custodia",
        }
    # Consultar la custodia de origen
    origen_inv_custodia = InvCustodia.query.get(origen_inv_custodia_id)
    if origen_inv_custodia is None:
        return {
            "success": False,
            "message": "Custodia de origen no encontrada",
        }
    # Consultar la custodia de destino
    destino_inv_custodia = InvCustodia.query.get(destino_inv_custodia_id)
    if destino_inv_custodia is None:
        return {
            "success": False,
            "message": "Custodia de destino no encontrada",
        }
    # En el cuerpo del POST, se espera un JSON con inv_equipo_id
    if "inv_equipo_id" not in request.json:
        return {
            "success": False,
            "message": "No se especificó el equipo a mover",
        }
    inv_equipo_id = request.json["inv_equipo_id"]
    # Consultar el InvEquipo a mover
    inv_equipo = InvEquipo.query.get(inv_equipo_id)
    if inv_equipo is None:
        return {
            "success": False,
            "message": "Equipo no encontrado",
        }
    # Mover el InvEquipo a la custodia de destino
    inv_equipo.inv_custodia_id = destino_inv_custodia.id
    inv_equipo.save()
    # Entregar JSON
    return {
        "success": True,
        "message": f"Equipo {inv_equipo_id} movido a la custodia {destino_inv_custodia.id}",
    }


@inv_custodias.route("/inv_custodias/nuevo")
@permission_required(MODULO, Permiso.CREAR)
def new():
    """Nueva Custodia 1. Elegir Usuario"""
    return render_template("inv_custodias/new_1_choose.jinja2")


@inv_custodias.route("/inv_custodias/nuevo/<int:usuario_id>", methods=["GET", "POST"])
@permission_required(MODULO, Permiso.CREAR)
def new_with_usuario_id(usuario_id):
    """Nueva Custodia 2. Crear"""
    # Consultar al usuario elegido
    usuario = Usuario.query.get_or_404(usuario_id)
    # Consultar las custodias que ya tenga el usuario
    tiene_inv_custodias = InvCustodia.query.filter_by(usuario_id=usuario.id, estatus="A").order_by(InvCustodia.id).count() > 0
    # Preparar el formulario
    form = InvCustodiaForm()
    if form.validate_on_submit():
        # Guardar
        inv_custodia = InvCustodia(
            usuario_id=usuario.id,
            fecha=form.fecha.data,
            curp=usuario.curp,
            nombre_completo=usuario.nombre,
            equipos_cantidad=0,
            equipos_fotos_cantidad=0,
        )
        inv_custodia.save()
        # Guardar bitácora
        bitacora = Bitacora(
            modulo=Modulo.query.filter_by(nombre=MODULO).first(),
            usuario=current_user,
            descripcion=safe_message(f"Nueva InvCustodia {inv_custodia.id} de {usuario.email}"),
            url=url_for("inv_custodias.detail", inv_custodia_id=inv_custodia.id),
        )
        bitacora.save()
        # Entregar detalle
        flash(bitacora.descripcion, "success")
        return redirect(bitacora.url)
    # Mostrar formulario con la fecha de hoy por defecto
    form.fecha.data = date.today()
    return render_template(
        "inv_custodias/new_2_create.jinja2",
        form=form,
        tiene_inv_custodias=tiene_inv_custodias,
        usuario=usuario,
    )


@inv_custodias.route("/inv_custodias/edicion/<int:inv_custodia_id>", methods=["GET", "POST"])
@permission_required(MODULO, Permiso.MODIFICAR)
def edit(inv_custodia_id):
    """Editar InvCustodia"""
    inv_custodia = InvCustodia.query.get_or_404(inv_custodia_id)
    form = InvCustodiaForm()
    if form.validate_on_submit():
        # Guardar
        inv_custodia.fecha = form.fecha.data
        inv_custodia.curp = inv_custodia.usuario.curp  # Actualizarlo desde su Usuario relacionado
        inv_custodia.nombre_completo = inv_custodia.usuario.nombre  # Actualizarlo desde su Usuario relacionado
        inv_custodia.save()
        # Guardar bitácora
        bitacora = Bitacora(
            modulo=Modulo.query.filter_by(nombre=MODULO).first(),
            usuario=current_user,
            descripcion=safe_message(f"Editado InvCustodia {inv_custodia.id} de {inv_custodia.usuario.email}"),
            url=url_for("inv_custodias.detail", inv_custodia_id=inv_custodia.id),
        )
        bitacora.save()
        # Entregar detalle
        flash(bitacora.descripcion, "success")
        return redirect(bitacora.url)
    form.fecha.data = inv_custodia.fecha
    return render_template("inv_custodias/edit.jinja2", form=form, inv_custodia=inv_custodia)


@inv_custodias.route("/inv_custodias/eliminar/<int:inv_custodia_id>")
@permission_required(MODULO, Permiso.ADMINISTRAR)
def delete(inv_custodia_id):
    """Eliminar InvCustodia"""
    inv_custodia = InvCustodia.query.get_or_404(inv_custodia_id)
    if inv_custodia.estatus == "A":
        # Eliminar InvCustodia
        inv_custodia.delete()
        # Eliminar los InvEquipos de la InvCustodia
        for inv_equipo in inv_custodia.inv_equipos:
            inv_equipo.delete()
            # Eliminar los InvComponentes de cada InvEquipo
            for inv_componente in inv_equipo.inv_componentes:
                inv_componente.delete()
        # Agregar a la bitácora
        bitacora = Bitacora(
            modulo=Modulo.query.filter_by(nombre=MODULO).first(),
            usuario=current_user,
            descripcion=safe_message(f"Eliminado InvCustodia {inv_custodia.id} de {inv_custodia.usuario.email}"),
            url=url_for("inv_custodias.detail", inv_custodia_id=inv_custodia.id),
        )
        bitacora.save()
        flash(bitacora.descripcion, "success")
    return redirect(url_for("inv_custodias.detail", inv_custodia_id=inv_custodia.id))


@inv_custodias.route("/inv_custodias/recuperar/<int:inv_custodia_id>")
@permission_required(MODULO, Permiso.ADMINISTRAR)
def recover(inv_custodia_id):
    """Recuperar InvCustodia"""
    inv_custodia = InvCustodia.query.get_or_404(inv_custodia_id)
    if inv_custodia.estatus == "B":
        # Recuperar InvCustodia
        inv_custodia.recover()
        # Recuperar los InvEquipos de la InvCustodia
        for inv_equipo in inv_custodia.inv_equipos:
            inv_equipo.recover()
            # Recuperar los InvComponentes de cada InvEquipo
            for inv_componente in inv_equipo.inv_componentes:
                inv_componente.recover()
        bitacora = Bitacora(
            modulo=Modulo.query.filter_by(nombre=MODULO).first(),
            usuario=current_user,
            descripcion=safe_message(f"Recuperado InvCustodia {inv_custodia.id} de {inv_custodia.usuario.email}"),
            url=url_for("inv_custodias.detail", inv_custodia_id=inv_custodia.id),
        )
        bitacora.save()
        flash(bitacora.descripcion, "success")
    return redirect(url_for("inv_custodias.detail", inv_custodia_id=inv_custodia.id))


@inv_custodias.route("/inv_custodias/tablero")
@permission_required(MODULO, Permiso.MODIFICAR)
def dashboard():
    """Tablero de InvCustodia"""
    # Cantidades de custodias por edificio
    inv_custodias_cantidades_por_edificio = (
        database.session.query(Domicilio.id, Domicilio.edificio, func.count(InvCustodia.id))
        .select_from(InvCustodia)
        .join(Usuario)
        .join(Oficina)
        .join(Domicilio)
        .where(InvCustodia.estatus == "A")
        .group_by(Domicilio.id, Domicilio.edificio)
        .order_by(Domicilio.edificio)
        .all()
    )
    # Entregar
    return render_template(
        "inv_custodias/dashboard.jinja2",
        inv_custodias_cantidades_por_edificio=inv_custodias_cantidades_por_edificio,
    )


@inv_custodias.route("/inv_custodias/exportar_reporte_xlsx/<int:domicilio_id>")
@permission_required(MODULO, Permiso.MODIFICAR)
def exportar_reporte_xlsx(domicilio_id):
    """Lanzar tarea en el fondo para exportar"""
    tarea = current_user.launch_task(
        comando="inv_custodias.tasks.lanzar_exportar_reporte_xlsx",
        mensaje="Exportando el reporte de custodias a un archivo XLSX...",
        domicilio_id=domicilio_id,
    )
    flash("Se ha lanzado esta tarea en el fondo. Esta página se va a recargar en 10 segundos...", "info")
    return redirect(url_for("tareas.detail", tarea_id=tarea.id))
