"""
Soportes Tickets, vistas
"""

import json
from flask import Blueprint, flash, redirect, render_template, request, url_for
from flask_login import current_user, login_required
from sqlalchemy import or_

from lib.datatables import get_datatable_parameters, output_datatable_json
from lib.safe_string import safe_string, safe_message, safe_clave

from hercules.blueprints.bitacoras.models import Bitacora
from hercules.blueprints.modulos.models import Modulo
from hercules.blueprints.permisos.models import Permiso
from hercules.blueprints.usuarios.decorators import permission_required
from hercules.blueprints.soportes_tickets.models import SoporteTicket
from hercules.blueprints.funcionarios.models import Funcionario
from hercules.blueprints.usuarios.models import Usuario
from hercules.blueprints.oficinas.models import Oficina
from hercules.blueprints.soportes_categorias.models import SoporteCategoria

# Roles necesarios
from .models import (
    ROL_INFORMATICA,
    ROL_INFRAESTRUCTURA,
)

MODULO = "SOPORTES TICKETS"

soportes_tickets = Blueprint("soportes_tickets", __name__, template_folder="templates")


@soportes_tickets.before_request
@login_required
@permission_required(MODULO, Permiso.VER)
def before_request():
    """Permiso por defecto"""


def _get_funcionario_if_is_soporte():
    """Consultar el funcionario (si es de soporte) a partir del usuario actual"""
    funcionario = Funcionario.query.filter(Funcionario.email == current_user.email).first()
    if funcionario is None:
        return None  # No existe el funcionario
    if funcionario.estatus != "A":
        return None  # No es activo
    if funcionario.en_soportes is False:
        return None  # No es de soporte
    return funcionario


def _owns_ticket(soporte_ticket: SoporteTicket):
    """Es propietario del ticket, porque lo creo, es de soporte o es administrador"""
    if current_user.can_admin(MODULO):
        return True  # Es administrador
    if _get_funcionario_if_is_soporte():
        return True  # Es de soporte
    if soporte_ticket.usuario == current_user:
        return True  # Es el usuario que creó el ticket
    return False


@soportes_tickets.route("/soportes_tickets/datatable_json", methods=["GET", "POST"])
def datatable_json():
    """DataTable JSON para listado de Tickets"""
    # Tomar parámetros de Datatables
    draw, start, rows_per_page = get_datatable_parameters()
    # Consultar
    consulta = SoporteTicket.query
    # Primero filtrar por columnas propias
    if "estatus" in request.form:
        consulta = consulta.filter(SoporteTicket.estatus == request.form["estatus"])
    else:
        consulta = consulta.filter(SoporteTicket.estatus == "A")
    if "soporte_ticket_id" in request.form:
        consulta = consulta.filter(SoporteTicket.id == request.form["soporte_ticket_id"])
    if "estado" in request.form:
        consulta = consulta.filter(SoporteTicket.estado == request.form["estado"])
    if "categoria_id" in request.form:
        consulta = consulta.filter(SoporteTicket.soporte_categoria_id == request.form["categoria_id"])
    # Luego filtrar por columnas de otras tablas
    if "usuario" in request.form:
        nombre = safe_string(request.form["usuario"], save_enie=True)
        if nombre != "":
            palabras = nombre.split()
            consulta = consulta.join(Usuario)
            for palabra in palabras:
                consulta = consulta.filter(
                    or_(
                        Usuario.nombres.contains(palabra),
                        Usuario.apellido_paterno.contains(palabra),
                        Usuario.apellido_materno.contains(palabra),
                    )
                )
    if "oficina" in request.form:
        if "usuario" not in request.form:
            consulta = consulta.join(Usuario)
        oficina = safe_clave(request.form["oficina"])
        if oficina != "":
            consulta = consulta.join(Oficina, Oficina.id == Usuario.oficina_id)
            consulta = consulta.filter(Oficina.clave.contains(oficina))
    if "categoria" in request.form:
        categoria = safe_string(request.form["categoria"])
        if categoria != "":
            consulta = consulta.join(SoporteCategoria)
            consulta = consulta.filter(SoporteCategoria.nombre.contains(categoria))

    # Ordenar y paginar
    registros = consulta.order_by(SoporteTicket.id.desc()).offset(start).limit(rows_per_page).all()
    total = consulta.count()
    # Elaborar datos para DataTable
    data = []
    for resultado in registros:
        data.append(
            {
                "detalle": {
                    "id": resultado.id,
                    "url": url_for("soportes_tickets.detail", soporte_ticket_id=resultado.id),
                },
                "usuario": {
                    "nombre": resultado.usuario.nombre,
                    "url": (
                        url_for("usuarios.detail", usuario_id=resultado.usuario_id) if current_user.can_view("USUARIOS") else ""
                    ),
                },
                "oficina": {
                    "clave": resultado.usuario.oficina.clave,
                    "nombre": resultado.usuario.oficina.descripcion_corta,
                    "url": (
                        url_for("oficinas.detail", oficina_id=resultado.usuario.oficina_id)
                        if current_user.can_view("OFICINAS")
                        else ""
                    ),
                },
                "estado": resultado.estado,
                "categoria": {
                    "nombre": resultado.soporte_categoria.nombre,
                    "url": (
                        url_for("soportes_categorias.detail", soporte_categoria_id=resultado.soporte_categoria.id)
                        if current_user.can_view("SOPORTES CATEGORIAS")
                        else ""
                    ),
                },
                "descripcion": resultado.descripcion,
                "creacion": resultado.creado.strftime("%Y-%m-%d %H:%M"),
                "tecnico": {
                    "nombre": resultado.funcionario.nombre,
                    "url": (
                        url_for("funcionarios.detail", funcionario_id=resultado.funcionario_id)
                        if current_user.can_view("FUNCIONARIOS")
                        else ""
                    ),
                },
                "solucion": resultado.soluciones if resultado.soluciones else "",
            }
        )
    # Entregar JSON
    return output_datatable_json(draw, total, data)


@soportes_tickets.route("/soportes_tickets")
def list_active():
    """Listado de Tickets activos"""
    return render_template(
        "soportes_tickets/list.jinja2",
        filtros=json.dumps({"estatus": "A"}),
        titulo="Tickets",
        estados=SoporteTicket.ESTADOS,
        estatus="A",
    )


@soportes_tickets.route("/soportes_tickets/inactivos")
@permission_required(MODULO, Permiso.ADMINISTRAR)
def list_inactive():
    """Listado de Tickets inactivos"""
    return render_template(
        "soportes_tickets/list.jinja2",
        filtros=json.dumps({"estatus": "B"}),
        titulo="Tickets inactivos",
        estados=SoporteTicket.ESTADOS,
        estatus="B",
    )


@soportes_tickets.route("/soportes_tickets/<int:soporte_ticket_id>")
def detail(soporte_ticket_id):
    """Detalle de un Ticket"""
    ticket = SoporteTicket.query.get_or_404(soporte_ticket_id)
    return render_template("soportes_tickets/detail.jinja2", ticket=ticket)
