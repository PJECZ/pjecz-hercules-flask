"""
Soportes Adjuntos Tickets, vistas
"""

import json
from flask import Blueprint, flash, redirect, render_template, request, url_for
from flask_login import current_user, login_required
from werkzeug.datastructures import CombinedMultiDict

from lib.datatables import get_datatable_parameters, output_datatable_json
from lib.safe_string import safe_string, safe_message
from lib.storage import GoogleCloudStorage

from hercules.blueprints.bitacoras.models import Bitacora
from hercules.blueprints.modulos.models import Modulo
from hercules.blueprints.permisos.models import Permiso
from hercules.blueprints.usuarios.decorators import permission_required
from hercules.blueprints.soportes_adjuntos.models import SoporteAdjunto
from hercules.blueprints.funcionarios.models import Funcionario
from hercules.blueprints.soportes_tickets.models import SoporteTicket

from hercules.blueprints.soportes_adjuntos.forms import SoporteAdjuntoNewForm

from lib.exceptions import MyUnknownExtensionError, MyNotAllowedExtensionError, MyMissingConfigurationError

MODULO = "SOPORTES ADJUNTOS"
SUBDIRECTORIO = "soportes_adjuntos"

soportes_adjuntos = Blueprint("soportes_adjuntos", __name__, template_folder="templates")


def _get_funcionario_from_current_user():
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
    if _get_funcionario_from_current_user():
        return True  # Es funcionario de soporte
    if soporte_ticket.usuario == current_user:
        return True  # Es el usuario que creo este ticket
    return False


@soportes_adjuntos.before_request
@login_required
@permission_required(MODULO, Permiso.VER)
def before_request():
    """Permiso por defecto"""


@soportes_adjuntos.route("/soportes_adjuntos/datatable_json", methods=["GET", "POST"])
def datatable_json():
    """DataTable JSON para listado de Adjuntos"""
    # Tomar parámetros de Datatables
    draw, start, rows_per_page = get_datatable_parameters()
    # Consultar
    consulta = SoporteAdjunto.query
    # Primero filtrar por columnas propias
    if "estatus" in request.form:
        consulta = consulta.filter_by(estatus=request.form["estatus"])
    else:
        consulta = consulta.filter_by(estatus="A")
    if "ticket_id" in request.form:
        consulta = consulta.filter_by(soporte_ticket_id=request.form["ticket_id"])
    # Luego filtrar por columnas de otras tablas
    # if "persona_rfc" in request.form:
    #     consulta = consulta.join(Persona)
    #     consulta = consulta.filter(Persona.rfc.contains(safe_rfc(request.form["persona_rfc"], search_fragment=True)))
    # Ordenar y paginar
    registros = consulta.order_by(SoporteAdjunto.id).offset(start).limit(rows_per_page).all()
    total = consulta.count()
    # Elaborar datos para DataTable
    data = []
    for resultado in registros:
        data.append(
            {
                "detalle": {
                    "nombre": resultado.archivo,
                    "url": url_for("soportes_adjuntos.detail", soporte_adjunto_id=resultado.id),
                },
                "descripcion": resultado.descripcion,
            }
        )
    # Entregar JSON
    return output_datatable_json(draw, total, data)


@soportes_adjuntos.route("/soportes_adjuntos/<int:soporte_adjunto_id>")
def detail(soporte_adjunto_id):
    """Detalle de un Ticket"""
    adjunto = SoporteAdjunto.query.get_or_404(soporte_adjunto_id)
    if not _owns_ticket(adjunto.soporte_ticket):
        flash("No tiene permiso para ver archivos adjuntos en ese ticket.", "warning")
        return redirect(url_for("soportes_tickets.list_active"))
    return render_template(
        "soportes_adjuntos/detail.jinja2",
        adjunto=adjunto,
        funcionario=_get_funcionario_from_current_user(),
    )


@soportes_adjuntos.route("/soportes_adjuntos/nuevo/<int:soporte_ticket_id>", methods=["GET", "POST"])
@permission_required(MODULO, Permiso.CREAR)
def new(soporte_ticket_id):
    """Adjuntar Archivos al Ticket"""
    ticket = SoporteTicket.query.get_or_404(soporte_ticket_id)
    if not _owns_ticket(ticket):
        flash("No tiene permiso para agregar archivos adjuntos en ese ticket.", "warning")
        return redirect(url_for("soportes_tickets.list_active"))
    detalle_url = url_for("soportes_tickets.detail", soporte_ticket_id=ticket.id)
    if ticket.estatus != "A":
        flash("No puede adjuntar un archivo a un ticket eliminado.", "warning")
        return redirect(detalle_url)
    if ticket.estado not in ("SIN ATENDER", "TRABAJANDO"):
        flash("No puede adjuntar un archivo a un ticket que no está abierto o trabajando.", "warning")
        return redirect(detalle_url)
    funcionario = _get_funcionario_from_current_user()
    if funcionario:
        funcionario_nombre = funcionario.nombre
    else:
        funcionario_nombre = current_user.email
    form = SoporteAdjuntoNewForm(CombinedMultiDict((request.files, request.form)))
    if form.validate_on_submit():
        es_valido = True
        # Validar la descripción
        descripcion = safe_string(form.descripcion.data)
        if descripcion == "":
            flash("La descripción es requerida.", "warning")
            es_valido = False
        # Validar el archivo
        archivo = request.files["archivo"]
        storage = GoogleCloudStorage(SUBDIRECTORIO)
        try:
            storage.set_content_type(archivo.filename)
        except MyNotAllowedExtensionError:
            flash("Tipo de archivo no permitido.", "warning")
            es_valido = False
        except MyUnknownExtensionError:
            flash("Tipo de archivo desconocido.", "warning")
            es_valido = False
        # Si es válido
        if es_valido:
            # Insertar el registro, para obtener el ID
            cit_archivo = SoporteAdjunto(
                soporte_ticket=ticket,
                descripcion=descripcion,
                archivo="",
                url="",
            )
            cit_archivo.save()
            # Subir el archivo a la nube
            try:
                storage.set_filename(hashed_id=cit_archivo.encode_id(), description=descripcion)
                storage.upload(archivo.stream.read())
                cit_archivo.archivo = archivo.filename  # Conservar el nombre original
                cit_archivo.url = storage.url
                cit_archivo.save()
            except MyMissingConfigurationError:
                flash("No se ha configurado el almacenamiento en la nube.", "warning")
            except Exception:
                flash("Error al subir el archivo.", "danger")
            # Registrar la acción en la bitácora
            bitacora = Bitacora(
                modulo=Modulo.query.filter_by(nombre=MODULO).first(),
                usuario=current_user,
                descripcion=safe_message(
                    f"Subida de archivo {cit_archivo.archivo} al ticket {ticket.id} por {funcionario_nombre}."
                ),
                url=detalle_url,
            )
            bitacora.save()
            flash(bitacora.descripcion, "success")
            return redirect(bitacora.url)
    form.usuario.data = ticket.usuario.nombre  # Read only
    form.problema.data = ticket.descripcion  # Read only
    form.categoria.data = ticket.soporte_categoria.nombre  # Read only
    return render_template("soportes_adjuntos/new.jinja2", form=form, soporte_ticket=ticket)
