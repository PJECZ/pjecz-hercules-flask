"""
Financieros Vales, vistas
"""

from datetime import datetime, time
import json
import re

from flask import Blueprint, flash, redirect, render_template, request, url_for
from flask_login import current_user, login_required
from pytz import timezone

from hercules.blueprints.bitacoras.models import Bitacora
from hercules.blueprints.fin_vales.models import FinVale
from hercules.blueprints.modulos.models import Modulo
from hercules.blueprints.permisos.models import Permiso
from hercules.blueprints.usuarios.decorators import permission_required
from hercules.blueprints.usuarios.models import Usuario
from lib.datatables import get_datatable_parameters, output_datatable_json
from lib.safe_string import safe_email, safe_message, safe_string

MODULO = "FIN VALES"

fin_vales = Blueprint("fin_vales", __name__, template_folder="templates")

# Roles que deben estar en la base de datos
ROL_SOLICITANTES = "FINANCIEROS SOLICITANTES"
ROL_AUTORIZANTES = "FINANCIEROS AUTORIZANTES"
ROL_ASISTENTES = "FINANCIEROS ASISTENTES"
ROLES_PUEDEN_VER = (ROL_SOLICITANTES, ROL_AUTORIZANTES, ROL_ASISTENTES)
ROLES_PUEDEN_IMPRIMIR = (ROL_AUTORIZANTES, ROL_ASISTENTES)

TIMEZONE = "America/Mexico_City"
local_tz = timezone(TIMEZONE)
medianoche = time.min


@fin_vales.before_request
@login_required
@permission_required(MODULO, Permiso.VER)
def before_request():
    """Permiso por defecto"""


@fin_vales.route("/fin_vales/datatable_json", methods=["GET", "POST"])
def datatable_json():
    """DataTable JSON para listado de FinVale"""
    # Tomar parámetros de Datatables
    draw, start, rows_per_page = get_datatable_parameters()
    # Consultar
    consulta = FinVale.query
    # Primero filtrar por columnas propias
    if "estatus" in request.form:
        consulta = consulta.filter(FinVale.estatus == request.form["estatus"])
    else:
        consulta = consulta.filter(FinVale.estatus == "A")
    if "fin_vale_id" in request.form:
        try:
            consulta = consulta.filter(FinVale.id == int(request.form["fin_vale_id"]))
        except ValueError:
            pass
    else:
        if "usuario_id" in request.form:
            consulta = consulta.filter(FinVale.usuario_id == request.form["usuario_id"])
        if "estado" in request.form:
            consulta = consulta.filter(FinVale.estado == request.form["estado"])
        if "justificacion" in request.form:
            justificacion = safe_string(request.form["justificacion"], do_unidecode=False, save_enie=True, to_uppercase=False)
            if justificacion != "":
                consulta = consulta.filter(FinVale.justificacion.ilike(f"%{justificacion}%"))
        creado_desde = None
        creado_hasta = None
        if "creado_desde" in request.form and re.match(r"\d{4}-\d{2}-\d{2}", request.form["creado_desde"]):
            creado_desde = request.form["creado_desde"]
        if "creado_hasta" in request.form and re.match(r"\d{4}-\d{2}-\d{2}", request.form["creado_hasta"]):
            creado_hasta = request.form["creado_hasta"]
        if creado_desde and creado_hasta and creado_desde > creado_hasta:
            creado_desde, creado_hasta = creado_hasta, creado_desde
        if creado_desde:
            year, month, day = map(int, creado_desde.split("-"))
            creado_desde_dt = datetime(year=year, month=month, day=day, hour=0, minute=0, second=0)
            consulta = consulta.filter(FinVale.creado >= creado_desde_dt)
        if creado_hasta:
            year, month, day = map(int, creado_hasta.split("-"))
            creado_hasta_dt = datetime(year=year, month=month, day=day, hour=23, minute=59, second=59)
            consulta = consulta.filter(FinVale.creado <= creado_hasta_dt)
    # Ordenar y paginar
    registros = consulta.order_by(FinVale.id.desc()).offset(start).limit(rows_per_page).all()
    total = consulta.count()
    # Elaborar datos para DataTable
    data = []
    for resultado in registros:
        data.append(
            {
                "detalle": {
                    "id": resultado.id,
                    "url": url_for("fin_vales.detail", fin_vale_id=resultado.id),
                },
                "creado": resultado.creado.strftime("%Y-%m-%d %H:%M:%S"),
                "usuario": {
                    "email": resultado.usuario.email,
                    "nombre": resultado.usuario.nombre,
                },
                "justificacion": resultado.justificacion,
                "monto": resultado.monto,
                "estado": resultado.estado,
            }
        )
    # Entregar JSON
    return output_datatable_json(draw, total, data)


@fin_vales.route("/fin_vales")
def list_active():
    """Listado de FinVale activos"""

    # Definir filtros por defecto, solo para el usuario actual
    filtros = {"usuario_id": current_user.id, "estatus": "A"}
    titulo = f"Vales de Gasolina de {current_user.nombre}"

    # Si es ADMINISTRADOR y viene usuario_id en la URL, agregar a los filtros
    if current_user.can_admin(MODULO):
        try:
            usuario_id = int(request.args.get("usuario_id"))
            usuario = Usuario.query.get_or_404(usuario_id)
            filtros = {"estatus": "A", "usuario_id": usuario_id}
            titulo = f"Administar los Vales de Gasolina de {usuario.nombre}"
        except (TypeError, ValueError):
            filtros = {"estatus": "A"}
            titulo = "Administrar todos los Vales de Gasolina"

    # Si es ROL_ASISTENTES, mostrar TODOS los vales de su oficina
    elif ROL_ASISTENTES in current_user.get_roles():
        filtros = {"estatus": "A"}
        titulo = "Asistir en Vales de Gasolina"

    # Si es ROL_AUTORIZANTES, mostrar Vales con estado SOLICITADO
    elif ROL_AUTORIZANTES in current_user.get_roles():
        filtros = {"estatus": "A", "estado": "SOLICITADO"}
        titulo = "Vales de Gasolina por autorizar"

    # Si es ROL_SOLICITANTES, mostrar Vales con estado CREADO
    elif ROL_SOLICITANTES in current_user.get_roles():
        filtros = {"estatus": "A", "estado": "CREADO"}
        titulo = "Vales de Gasolina por solicitar"

    # Entregar
    return render_template(
        "fin_vales/list.jinja2",
        filtros=json.dumps(filtros),
        titulo=titulo,
        estatus="A",
    )


@fin_vales.route("/fin_vales/inactivos")
@permission_required(MODULO, Permiso.ADMINISTRAR)
def list_inactive():
    """Listado de FinVale inactivos"""
    return render_template(
        "fin_vales/list.jinja2",
        filtros=json.dumps({"estatus": "B"}),
        titulo="Vales inactivos",
        estatus="B",
    )


@fin_vales.route("/fin_vales/<int:fin_vale_id>")
def detail(fin_vale_id):
    """Detalle de un FinVale"""

    # Consultar el vale
    fin_vale = FinVale.query.get_or_404(fin_vale_id)

    # Inicializar las variables de la efirma por defecto
    efirma_sello_digital = None
    efirma_url = None
    efirma_qr_url = None

    # Si el estado es SOLICITADO
    if fin_vale.estado == "SOLICITADO":
        efirma_sello_digital = fin_vale.solicito_efirma_sello_digital
        efirma_url = fin_vale.solicito_efirma_url
        efirma_qr_url = fin_vale.solicito_efirma_qr_url

    # Si el estado es AUTORIZADO
    if fin_vale.estado == "AUTORIZADO":
        efirma_sello_digital = fin_vale.autorizo_efirma_sello_digital
        efirma_url = fin_vale.autorizo_efirma_url
        efirma_qr_url = fin_vale.autorizo_efirma_qr_url

    # Inicializar la variable de si puede verlo
    puede_verlo = False

    # Si es administrador, puede verlo
    if current_user.can_admin(MODULO):
        puede_verlo = True

    # Si tiene uno de los roles que pueden verlo y esta activo, puede verlo
    if set(current_user.get_roles()).intersection(ROLES_PUEDEN_VER) and fin_vale.estatus == "A":
        puede_verlo = True

    # Si es el usuario que lo creo y esta activo, puede verlo
    if fin_vale.usuario_id == current_user.id and fin_vale.estatus == "A":
        puede_verlo = True

    # Si puede verlo
    if puede_verlo:
        return render_template(
            "fin_vales/detail.jinja2",
            fin_vale=fin_vale,
            efirma_sello_digital=efirma_sello_digital,
            efirma_url=efirma_url,
            efirma_qr_url=efirma_qr_url,
        )

    # No puede verlo
    flash("No tiene permiso para ver este vale.", "warning")
    return redirect(url_for("fin_vales.list_active"))


@fin_vales.route("/fin_vales/imprimir/<int:fin_vale_id>")
def print(fin_vale_id):
    """Imprimir un FinVale"""

    # Consultar el vale
    fin_vale = FinVale.query.get_or_404(fin_vale_id)

    # Determinar el sello digital y la URL de la firma electronica
    efirma_sello_digital = None
    efirma_url = None
    efirma_qr_url = None
    efirma_motivo = None

    # Si el estado es...
    if fin_vale.estado == "SOLICITADO":
        efirma_sello_digital = fin_vale.solicito_efirma_sello_digital
        efirma_url = fin_vale.solicito_efirma_url
        efirma_qr_url = fin_vale.solicito_efirma_qr_url
    elif fin_vale.estado == "CANCELADO POR SOLICITANTE":
        efirma_sello_digital = fin_vale.solicito_efirma_sello_digital
        efirma_url = fin_vale.solicito_efirma_url
        efirma_qr_url = fin_vale.solicito_efirma_qr_url
        efirma_motivo = fin_vale.solicito_cancelo_motivo
    elif fin_vale.estado == "AUTORIZADO":
        efirma_sello_digital = fin_vale.autorizo_efirma_sello_digital
        efirma_url = fin_vale.autorizo_efirma_url
        efirma_qr_url = fin_vale.autorizo_efirma_qr_url
    elif fin_vale.estado == "CANCELADO POR AUTORIZANTE":
        efirma_sello_digital = fin_vale.autorizo_efirma_sello_digital
        efirma_url = fin_vale.autorizo_efirma_url
        efirma_qr_url = fin_vale.autorizo_efirma_qr_url
        efirma_motivo = fin_vale.autorizo_cancelo_motivo

    # Validar que pueda verlo
    puede_imprimirlo = False

    # Si es administrador, puede imprimirlo
    if current_user.can_admin(MODULO):
        puede_imprimirlo = True

    # Si tiene uno de los roles que pueden imprimir y esta activo, puede imprimirlo
    if set(current_user.get_roles()).intersection(ROLES_PUEDEN_IMPRIMIR) and fin_vale.estatus == "A":
        puede_imprimirlo = True

    # Si es el usuario que lo creo y esta activo, puede imprimirlo
    if fin_vale.usuario_id == current_user.id and fin_vale.estatus == "A":
        puede_imprimirlo = True

    # Si puede imprimirlo
    if puede_imprimirlo:
        # Cortar las lineas del sello digital insertando saltos de linea cada 40 caracteres
        if efirma_sello_digital is not None:
            efirma_sello_digital = "<br>".join(
                [efirma_sello_digital[i : i + 40] for i in range(0, len(efirma_sello_digital), 40)]
            )
        # Mostrar la plantilla para imprimir
        return render_template(
            "fin_vales/print.jinja2",
            fin_vale=fin_vale,
            efirma_sello_digital=efirma_sello_digital,
            efirma_url=efirma_url,
            efirma_qr_url=efirma_qr_url,
            efirma_motivo=efirma_motivo,
        )

    # No puede imprimirlo
    flash("No tiene permiso para imprimir este Vale", "warning")
    return redirect(url_for("fin_vales.detail", fin_vale_id=fin_vale_id))
