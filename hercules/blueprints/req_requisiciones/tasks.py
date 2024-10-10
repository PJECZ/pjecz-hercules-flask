"""
Requisiciones, tareas en el fondo
"""
from datetime import datetime
import json
import logging
import os

from dotenv import load_dotenv
import requests
from lib.exceptions import (
    MyAnyError,
    MyConnectionError,
    MyMissingConfigurationError,
    MyNotValidParamError,
    MyStatusCodeError,
    MyRequestError,
    MyResponseError,
)
from lib.safe_string import safe_string

from lib.tasks import set_task_progress, set_task_error

from hercules.app import create_app
from hercules.blueprints.req_requisiciones.models import ReqRequisicion
from hercules.blueprints.usuarios.models import Usuario

load_dotenv()  # Take environment variables from .env
REQ_REQUISICIONES_EFIRMA_SER_FIRMA_CADENA_URL = os.getenv("REQ_REQUISICIONES_EFIRMA_SER_FIRMA_CADENA_URL")
REQ_REQUISICIONES_EFIRMA_CAN_FIRMA_CADENA_URL = os.getenv("REQ_REQUISICIONES_EFIRMA_CAN_FIRMA_CADENA_URL")
REQ_REQUISICIONES_EFIRMA_QR_URL = os.getenv("REQ_REQUISICIONES_EFIRMA_QR_URL")
REQ_REQUISICIONES_EFIRMA_APP_ID = os.getenv("REQ_REQUISICIONES_EFIRMA_APP_ID")
REQ_REQUISICIONES_EFIRMA_APP_PASS = os.getenv("REQ_REQUISICIONES_EFIRMA_APP_PASS")

# Roles que deben estar en la base de datos
ROL_SOLICITANTES = "REQUISICIONES SOLICITANTES"
ROL_AUTORIZANTES = "REQUISICIONES AUTORIZANTES"
ROL_REVISANTES = "REQUISICIONES REVISANTES"

TIMEOUT = 24  # Segundos de espera para la respuesta del motor de firma

bitacora = logging.getLogger(__name__)
bitacora.setLevel(logging.INFO)
formato = logging.Formatter("%(asctime)s:%(levelname)s:%(message)s")
empunadura = logging.FileHandler("req_requisiciones.log")
empunadura.setFormatter(formato)
bitacora.addHandler(empunadura)

app = create_app()
app.app_context().push()


def solicitar(req_requisicion_id: int, usuario_id: int, contrasena: str):
    """Firmar electronicamente la requisición por quien solicita"""

    # Validar configuracion
    if REQ_REQUISICIONES_EFIRMA_SER_FIRMA_CADENA_URL is None:
        mensaje = "Falta configurar REQ_REQUISICIONES_EFIRMA_SER_FIRMA_CADENA_URL"
        bitacora.error(mensaje)
        raise MyMissingConfigurationError(mensaje)
    if REQ_REQUISICIONES_EFIRMA_QR_URL is None:
        mensaje = "Falta configurar REQ_REQUISICIONES_EFIRMA_QR_URL"
        bitacora.error(mensaje)
        raise MyMissingConfigurationError(mensaje)
    if REQ_REQUISICIONES_EFIRMA_APP_ID is None:
        mensaje = "Falta configurar REQ_REQUISICIONES_EFIRMA_APP_ID"
        bitacora.error(mensaje)
        raise MyMissingConfigurationError(mensaje)
    if REQ_REQUISICIONES_EFIRMA_APP_PASS is None:
        mensaje = "Falta configurar REQ_REQUISICIONES_EFIRMA_APP_PASS"
        bitacora.error(mensaje)
        raise MyMissingConfigurationError(mensaje)

    # Consultar la requisicion
    req_requisicion = ReqRequisicion.query.get(req_requisicion_id)
    if req_requisicion is None:
        mensaje = f"No se encontró la requisición {req_requisicion_id}"
        bitacora.error(mensaje)
        raise MyNotValidParamError(mensaje)
    if req_requisicion.estatus != "A":
        mensaje = f"La requisición {req_requisicion_id} esta eliminada"
        bitacora.error(mensaje)
        raise MyNotValidParamError(mensaje)
    if req_requisicion.estado != "CREADO":
        mensaje = f"La requisición {req_requisicion_id} no está en estado CREADO"
        bitacora.error(mensaje)
        raise MyNotValidParamError(mensaje)

    # Consultar el usuario que solicita
    solicita = Usuario.query.get(usuario_id)
    if solicita is None:
        mensaje = f"No se encontró el usuario {usuario_id} que solicita"
        bitacora.error(mensaje)
        raise MyNotValidParamError(mensaje)
    if solicita.efirma_registro_id is None or solicita.efirma_registro_id == 0:
        mensaje = f"El usuario {solicita.email} no tiene registro en el motor de firma"
        bitacora.error(mensaje)
        raise MyNotValidParamError(mensaje)
    if ROL_SOLICITANTES not in solicita.get_roles():
        mensaje = f"El usuario {solicita.email} no tiene el rol {ROL_SOLICITANTES}"
        bitacora.error(mensaje)
        raise MyNotValidParamError(mensaje)

    # Juntar los elementos de la requisición para armar la cadena
    elementos = {
        "id": req_requisicion.id,
        "creado": req_requisicion.creado.strftime("%Y-%m-%d %H:%M:%S"),
        "glosa": req_requisicion.glosa,
        "solicito_nombre": solicita.nombre,
        "solicito_puesto": solicita.puesto,
        "solicito_email": solicita.email,
    }

    # Preparar los datos que se van a enviar al motor de firma
    data = {
        "cadenaOriginal": json.dumps(elementos),
        "idRegistro": solicita.efirma_registro_id,
        "contrasenaRegistro": contrasena,
        "idAplicacion": REQ_REQUISICIONES_EFIRMA_APP_ID,
        "contrasenaAplicacion": REQ_REQUISICIONES_EFIRMA_APP_PASS,
        "referencia": req_requisicion_id,
        "verificarUrl": True,
    }

    # Enviar la solicitud al motor de firma
    try:
        response = requests.post(
            REQ_REQUISICIONES_EFIRMA_SER_FIRMA_CADENA_URL,
            data=data,
            timeout=TIMEOUT,
            verify=False,
        )
        response.raise_for_status()
    except requests.exceptions.ConnectionError as error:
        mensaje = "Error de conexion al solicitar la requisición. " + safe_string(str(error))
        req_requisicion.solicito_efirma_error = mensaje
        req_requisicion.save()
        bitacora.error(mensaje)
        raise MyConnectionError(mensaje)
    except requests.exceptions.HTTPError as error:
        mensaje = "Error porque la respuesta no tiene el estado 200 al solicitar la requisición. " + safe_string(str(error))
        req_requisicion.solicito_efirma_error = mensaje
        req_requisicion.save()
        bitacora.error(mensaje)
        raise MyStatusCodeError(mensaje)
    except requests.exceptions.RequestException as error:
        mensaje = "Error desconocido al solicitar la requisición. " + safe_string(str(error))
        req_requisicion.solicito_efirma_error = mensaje
        req_requisicion.save()
        bitacora.error(mensaje)
        raise MyRequestError(mensaje)

    # Tomar el texto de la respuesta
    texto = response.text

    # Si la contraseña es incorrecta, se registra el error
    if texto == "Contraseña incorrecta":
        mensaje = "Error porque la contraseña es incorrecta al solicitar la requisición."
        req_requisicion.solicito_efirma_error = mensaje
        req_requisicion.save()
        bitacora.error(mensaje)
        raise MyResponseError(mensaje)

    # Convertir el texto a un diccionario
    texto = response.text.replace('"{', "{").replace('}"', "}")
    try:
        datos = json.loads(texto)
    except json.JSONDecodeError:
        mensaje = "Error al solicitar la requisición porque la respuesta no es JSON."
        req_requisicion.solicito_efirma_error = mensaje
        req_requisicion.save()
        bitacora.error(mensaje)
        raise MyResponseError(mensaje)

    # Ejemplo de la respuesta
    #   "success": true,
    #   "folio": 000001,
    #   "mensaje": "La operación se ha realizado exitosamente.",
    #   "cadenaOriginal": "",
    #   "fecha": "27/06/2022 13:47:11",
    #   "selloDigital": "",
    #   "url": "https://servidor/eFirmaServicios/verificaFirmaCadena.do?verificar=XXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXX",
    #   "ip": "172.1.1.1",
    #   "huella": "Primer mensaje de prueba"

    # Si el motor de firma entrega "success" en false, se registra el error
    if datos["success"] is False:
        mensaje = "Error al solicitar la requisición con este mensaje: " + str(datos["mensaje"])
        req_requisicion.solicito_efirma_error = mensaje
        req_requisicion.save()
        bitacora.error(mensaje)
        raise MyResponseError(mensaje)

    # Actualizar el vale, ahora su estado es SOLICITADO
    req_requisicion.solicito_nombre = solicita.nombre
    req_requisicion.solicito_puesto = solicita.puesto
    req_requisicion.solicito_email = solicita.email
    req_requisicion.solicito_efirma_tiempo = datetime.strptime(datos["fecha"], "%d/%m/%Y %H:%M:%S")
    req_requisicion.solicito_efirma_folio = datos["folio"]
    req_requisicion.solicito_efirma_sello_digital = datos["selloDigital"]
    req_requisicion.solicito_efirma_url = datos["url"]
    req_requisicion.solicito_efirma_qr_url = f"{REQ_REQUISICIONES_EFIRMA_QR_URL}?size=300&qrtext={datos['url']}"
    req_requisicion.solicito_efirma_mensaje = datos["mensaje"]
    req_requisicion.solicito_efirma_error = ""
    req_requisicion.estado = "SOLICITADO"
    req_requisicion.save()

    # Terminar tarea
    mensaje_final = f"Requisición {req_requisicion_id} solicitada"
    set_task_progress(progress=100, message=mensaje_final)
    bitacora.info(mensaje_final)
    return mensaje_final


def cancelar_solicitar(req_requisicion_id: int, contrasena: str, motivo: str):
    """Cancelar la firma electronica de una requisición por quien solicita"""

    # Validar configuracion
    if REQ_REQUISICIONES_EFIRMA_CAN_FIRMA_CADENA_URL is None:
        mensaje = "Falta configurar REQ_REQUISICIONES_EFIRMA_CAN_FIRMA_CADENA_URL"
        bitacora.error(mensaje)
        raise MyMissingConfigurationError(mensaje)
    if REQ_REQUISICIONES_EFIRMA_APP_ID is None:
        mensaje = "Falta configurar REQ_REQUISICIONES_EFIRMA_APP_ID"
        bitacora.error(mensaje)
        raise MyMissingConfigurationError(mensaje)
    if REQ_REQUISICIONES_EFIRMA_APP_PASS is None:
        mensaje = "Falta configurar REQ_REQUISICIONES_EFIRMA_APP_PASS"
        bitacora.error(mensaje)
        raise MyMissingConfigurationError(mensaje)

    # Consultar la requisición
    req_requisicion = ReqRequisicion.query.get(req_requisicion_id)
    if req_requisicion is None:
        mensaje = f"No se encontró la requisición {req_requisicion_id}"
        bitacora.error(mensaje)
        raise MyNotValidParamError(mensaje)
    if req_requisicion.estatus != "A":
        mensaje = f"La requisición {req_requisicion_id} esta eliminada"
        bitacora.error(mensaje)
        raise MyNotValidParamError(mensaje)
    if req_requisicion.estado != "SOLICITADO":
        mensaje = f"La requisición {req_requisicion_id} no está en estado SOLICITADO"
        bitacora.error(mensaje)
        raise MyNotValidParamError(mensaje)
    if req_requisicion.solicito_efirma_folio is None:
        mensaje = f"La requisición {req_requisicion_id} no tiene folio de solicitud"
        bitacora.error(mensaje)
        raise MyNotValidParamError(mensaje)

    # Consultar el usuario que solicita, para cancelar la firma
    solicita = Usuario.query.filter_by(email=req_requisicion.solicito_email).first()
    if solicita is None:
        mensaje = f"No se encontró el usuario {req_requisicion.solicito_email} que solicita"
        bitacora.error(mensaje)
        raise MyNotValidParamError(mensaje)
    if solicita.efirma_registro_id is None or solicita.efirma_registro_id == 0:
        mensaje = f"El usuario {req_requisicion.solicito_email} no tiene registro en el motor de firma"
        bitacora.error(mensaje)
        raise MyNotValidParamError(mensaje)
    if ROL_SOLICITANTES not in solicita.get_roles():
        mensaje = f"El usuario {solicita.email} no tiene el rol {ROL_SOLICITANTES}"
        bitacora.error(mensaje)
        raise MyNotValidParamError(mensaje)

    # Preparar los datos que se van a enviar al motor de firma
    data = {
        "idAplicacion": REQ_REQUISICIONES_EFIRMA_APP_ID,
        "contrasenaAplicacion": REQ_REQUISICIONES_EFIRMA_APP_PASS,
        "idRegistro": solicita.efirma_registro_id,
        "contrasenaRegistro": contrasena,
        "folios": req_requisicion.solicito_efirma_folio,
    }

    # Enviar la cancelacion al motor de firma
    try:
        response = requests.post(
            REQ_REQUISICIONES_EFIRMA_CAN_FIRMA_CADENA_URL,
            data=data,
            timeout=TIMEOUT,
            verify=False,
        )
        response.raise_for_status()
    except requests.exceptions.ConnectionError as error:
        mensaje = "Error de conexion al cancelar la requisición. " + safe_string(str(error))
        req_requisicion.solicito_efirma_error = mensaje
        req_requisicion.save()
        bitacora.error(mensaje)
        raise MyConnectionError(mensaje)
    except requests.exceptions.HTTPError as error:
        mensaje = "Error porque la respuesta no tiene el estado 200 al cancelar la requisición. " + safe_string(str(error))
        req_requisicion.solicito_efirma_error = mensaje
        req_requisicion.save()
        bitacora.error(mensaje)
        raise MyStatusCodeError(mensaje)
    except requests.exceptions.RequestException as error:
        mensaje = "Error desconocido al cancelar la requisición. " + safe_string(str(error))
        req_requisicion.solicito_efirma_error = mensaje
        req_requisicion.save()
        bitacora.error(mensaje)
        raise MyRequestError(mensaje)

    # Tomar el texto de la respuesta
    texto = response.text

    # Si la contraseña es incorrecta, se registra el error
    if texto == "Contraseña incorrecta":
        mensaje = "Error porque la contraseña es incorrecta al solicitar la requisición."
        req_requisicion.solicito_efirma_error = mensaje
        req_requisicion.save()
        bitacora.error(mensaje)
        raise MyRequestError(mensaje)

    # Convertir el texto a un diccionario
    texto = response.text.replace('"{', "{").replace('}"', "}")
    try:
        _ = json.loads(texto)
    except json.JSONDecodeError:
        mensaje = "Error al solicitar la requisición porque la respuesta no es JSON."
        req_requisicion.solicito_efirma_error = mensaje
        req_requisicion.save()
        bitacora.error(mensaje)
        raise MyRequestError(mensaje)

    # Ejemplo de la respuesta
    #   "estatus": "SELLO CANCELADO"
    #   "fechaCancelado": 2022-07-04 12:39:08.0

    # Actualizar la requisición, ahora su estado es CANCELADO POR SOLICITANTE
    req_requisicion.estado = "CANCELADO POR SOLICITANTE"
    req_requisicion.solicito_cancelo_tiempo = datetime.now()
    req_requisicion.solicito_cancelo_motivo = safe_string(motivo, to_uppercase=False)
    req_requisicion.solicito_cancelo_error = ""
    req_requisicion.save()

    # Terminar tarea
    mensaje_final = f"Requisición {req_requisicion_id} cancelado su solicitud"
    set_task_progress(progress=100, message=mensaje_final)
    bitacora.info(mensaje_final)
    return mensaje_final


def autorizar(req_requisicion_id: int, usuario_id: int, contrasena: str):
    """Firmar electronicamente la requisición por quien autoriza"""

    # Validar configuracion
    if REQ_REQUISICIONES_EFIRMA_SER_FIRMA_CADENA_URL is None:
        mensaje = "Falta configurar REQ_REQUISICIONES_EFIRMA_SER_FIRMA_CADENA_URL"
        bitacora.error(mensaje)
        return set_task_error(mensaje)
    if REQ_REQUISICIONES_EFIRMA_QR_URL is None:
        mensaje = "Falta configurar REQ_REQUISICIONES_EFIRMA_QR_URL"
        bitacora.error(mensaje)
        return set_task_error(mensaje)
    if REQ_REQUISICIONES_EFIRMA_APP_ID is None:
        mensaje = "Falta configurar REQ_REQUISICIONES_EFIRMA_APP_ID"
        bitacora.error(mensaje)
        return set_task_error(mensaje)
    if REQ_REQUISICIONES_EFIRMA_APP_PASS is None:
        mensaje = "Falta configurar REQ_REQUISICIONES_EFIRMA_APP_PASS"
        bitacora.error(mensaje)
        return set_task_error(mensaje)

    # Consultar la requisición
    req_requisicion = ReqRequisicion.query.get(req_requisicion_id)
    if req_requisicion is None:
        mensaje = f"No se encontró la requisición {req_requisicion_id}"
        bitacora.error(mensaje)
        return set_task_error(mensaje)
    if req_requisicion.estatus != "A":
        mensaje = f"La requisición {req_requisicion_id} esta eliminada"
        bitacora.error(mensaje)
        return set_task_error(mensaje)
    if req_requisicion.estado != "SOLICITADO":
        mensaje = f"La requisición {req_requisicion_id} no está en estado SOLICITADO"
        bitacora.error(mensaje)
        return set_task_error(mensaje)

    # Consultar el usuario que autoriza
    autoriza = Usuario.query.get(usuario_id)
    if autoriza is None:
        mensaje = f"No se encontró el usuario {usuario_id} que autoriza"
        bitacora.error(mensaje)
        return set_task_error(mensaje)
    if autoriza.efirma_registro_id is None or autoriza.efirma_registro_id == 0:
        mensaje = f"El usuario {autoriza.email} no tiene registro en el motor de firma"
        bitacora.error(mensaje)
        return set_task_error(mensaje)

    # Juntar los elementos de la requisición para armar la cadena
    elementos = {
        "id": req_requisicion.id,
        "autorizo_nombre": autoriza.nombre,
        "autorizo_puesto": autoriza.puesto,
        "autorizo_email": autoriza.email,
        "creado": req_requisicion.creado.strftime("%Y-%m-%d %H:%M:%S"),
        "solicito_nombre": req_requisicion.solicito_nombre,
        "solicito_puesto": req_requisicion.solicito_puesto,
        "solicito_email": req_requisicion.solicito_email,
    }

    # Preparar los datos que se van a enviar al motor de firma
    data = {
        "cadenaOriginal": json.dumps(elementos),
        "idRegistro": autoriza.efirma_registro_id,
        "contrasenaRegistro": contrasena,
        "idAplicacion": REQ_REQUISICIONES_EFIRMA_APP_ID,
        "contrasenaAplicacion": REQ_REQUISICIONES_EFIRMA_APP_PASS,
        "referencia": req_requisicion_id,
        "verificarUrl": True,
    }

    # Enviar la autorizacion al motor de firma
    try:
        response = requests.post(
            REQ_REQUISICIONES_EFIRMA_SER_FIRMA_CADENA_URL,
            data=data,
            timeout=TIMEOUT,
            verify=False,
        )
        response.raise_for_status()
    except requests.exceptions.ConnectionError as error:
        mensaje = "Error de conexion al autorizar la requisición." + safe_string(str(error))
        req_requisicion.autorizo_efirma_error = mensaje
        req_requisicion.save()
        bitacora.error(mensaje)
        return set_task_error(mensaje)
    except requests.exceptions.HTTPError as error:
        mensaje = "Error porque la respuesta no tiene el estado 200 al autorizar la requisición. " + safe_string(str(error))
        req_requisicion.autorizo_efirma_error = mensaje
        req_requisicion.save()
        bitacora.error(mensaje)
        return set_task_error(mensaje)
    except requests.exceptions.RequestException as error:
        mensaje = "Error desconocido al autorizar la requisición. " + safe_string(str(error))
        req_requisicion.autorizo_efirma_error = mensaje
        req_requisicion.save()
        bitacora.error(mensaje)
        return set_task_error(mensaje)

    # Tomar el texto de la respuesta
    texto = response.text

    # Si la contraseña es incorrecta, se registra el error
    if texto == "Contraseña incorrecta":
        mensaje = "Error porque la contraseña es incorrecta al autorizar la requsición."
        req_requisicion.autorizo_efirma_error = mensaje
        req_requisicion.save()
        bitacora.error(mensaje)
        return set_task_error(mensaje)

    # Convertir el texto a un diccionario
    texto = response.text.replace('"{', "{").replace('}"', "}")
    try:
        datos = json.loads(texto)
    except json.JSONDecodeError:
        mensaje = "Error al autorizar la requisición porque la respuesta no es JSON."
        req_requisicion.autorizo_efirma_error = mensaje
        req_requisicion.save()
        bitacora.error(mensaje)
        return set_task_error(mensaje)

    # Si el motor de firma entrega "success" en false, se registra el error
    if datos["success"] is False:
        mensaje = "Error al autorizar la requisición con este mensaje: " + str(datos["mensaje"])
        req_requisicion.autorizo_efirma_error = mensaje
        req_requisicion.save()
        bitacora.error(mensaje)
        return set_task_error(mensaje)

    # Actualizar la requisición, ahora su estado es AUTORIZADO
    req_requisicion.autorizo_nombre = autoriza.nombre
    req_requisicion.autorizo_puesto = autoriza.puesto
    req_requisicion.autorizo_email = autoriza.email
    req_requisicion.autorizo_efirma_tiempo = datetime.strptime(datos["fecha"], "%d/%m/%Y %H:%M:%S")
    req_requisicion.autorizo_efirma_folio = datos["folio"]
    req_requisicion.autorizo_efirma_sello_digital = datos["selloDigital"]
    req_requisicion.autorizo_efirma_url = datos["url"]
    req_requisicion.autorizo_efirma_qr_url = f"{REQ_REQUISICIONES_EFIRMA_QR_URL}?size=300&qrtext={datos['url']}"
    req_requisicion.autorizo_efirma_mensaje = datos["mensaje"]
    req_requisicion.autorizo_efirma_error = ""
    req_requisicion.estado = "AUTORIZADO"
    req_requisicion.save()

    # Terminar tarea
    mensaje_final = f"Requisición {req_requisicion.glosa} autorizada"
    set_task_progress(progress=100, message=mensaje_final)
    bitacora.info(mensaje_final)
    return mensaje_final


def cancelar_autorizar(req_requisicion_id: int, contrasena: str, motivo: str):
    """Cancelar la firma electronica de una requisición por quien autoriza"""

    # Validar configuracion
    if REQ_REQUISICIONES_EFIRMA_CAN_FIRMA_CADENA_URL is None:
        mensaje = "Falta configurar REQ_REQUISICIONES_EFIRMA_CAN_FIRMA_CADENA_URL"
        bitacora.error(mensaje)
        raise MyMissingConfigurationError(mensaje)
    if REQ_REQUISICIONES_EFIRMA_APP_ID is None:
        mensaje = "Falta configurar REQ_REQUISICIONES_EFIRMA_APP_ID"
        bitacora.error(mensaje)
        raise MyMissingConfigurationError(mensaje)
    if REQ_REQUISICIONES_EFIRMA_APP_PASS is None:
        mensaje = "Falta configurar REQ_REQUISICIONES_EFIRMA_APP_PASS"
        bitacora.error(mensaje)
        raise MyMissingConfigurationError(mensaje)

    # Consultar la requisición
    req_requisicion = ReqRequisicion.query.get(req_requisicion_id)
    if req_requisicion is None:
        mensaje = f"No se encontró la requisición {req_requisicion_id}"
        bitacora.error(mensaje)
        raise MyNotValidParamError(mensaje)
    if req_requisicion.estatus != "A":
        mensaje = f"La requisición {req_requisicion_id} esta eliminada"
        bitacora.error(mensaje)
        raise MyNotValidParamError(mensaje)
    if req_requisicion.estado != "AUTORIZADO":
        mensaje = f"La requisición {req_requisicion_id} no está en estado AUTORIZADO"
        bitacora.error(mensaje)
        raise MyNotValidParamError(mensaje)
    if req_requisicion.autorizo_efirma_folio is None:
        mensaje = f"La requisición {req_requisicion_id} no tiene folio de autorizado"
        bitacora.error(mensaje)
        raise MyNotValidParamError(mensaje)

    # Consultar el usuario que autoriza, para cancelar la firma
    autoriza = Usuario.query.filter_by(email=req_requisicion.autorizo_email).first()
    if autoriza is None:
        mensaje = f"No se encontró el usuario {req_requisicion.autorizo_email} que autoriza"
        bitacora.error(mensaje)
        raise MyNotValidParamError(mensaje)
    if autoriza.efirma_registro_id is None or autoriza.efirma_registro_id == 0:
        mensaje = f"El usuario {req_requisicion.autorizo_email} no tiene registro en el motor de firma"
        bitacora.error(mensaje)
        raise MyNotValidParamError(mensaje)
    if ROL_AUTORIZANTES not in autoriza.get_roles():
        mensaje = f"El usuario {autoriza.email} no tiene el rol {ROL_AUTORIZANTES}"
        bitacora.error(mensaje)
        raise MyNotValidParamError(mensaje)

    # Preparar los datos que se van a enviar al motor de firma
    data = {
        "idAplicacion": REQ_REQUISICIONES_EFIRMA_APP_ID,
        "contrasenaAplicacion": REQ_REQUISICIONES_EFIRMA_APP_PASS,
        "idRegistro": autoriza.efirma_registro_id,
        "contrasenaRegistro": contrasena,
        "folios": req_requisicion.autorizo_efirma_folio,
    }

    # Enviar la cancelacion al motor de firma
    try:
        response = requests.post(
            REQ_REQUISICIONES_EFIRMA_CAN_FIRMA_CADENA_URL,
            data=data,
            timeout=TIMEOUT,
            verify=False,
        )
        response.raise_for_status()
    except requests.exceptions.ConnectionError as error:
        mensaje = "Error de conexion al cancelar la requisición. " + safe_string(str(error))
        req_requisicion.autorizo_efirma_error = mensaje
        req_requisicion.save()
        bitacora.error(mensaje)
        raise MyConnectionError(mensaje)
    except requests.exceptions.HTTPError as error:
        mensaje = "Error porque la respuesta no tiene el estado 200 al cancelar la requisición. " + safe_string(str(error))
        req_requisicion.autorizo_efirma_error = mensaje
        req_requisicion.save()
        bitacora.error(mensaje)
        raise MyStatusCodeError(mensaje)
    except requests.exceptions.RequestException as error:
        mensaje = "Error desconocido al cancelar la requisición. " + safe_string(str(error))
        req_requisicion.autorizo_efirma_error = mensaje
        req_requisicion.save()
        bitacora.error(mensaje)
        raise MyRequestError(mensaje)

    # Tomar el texto de la respuesta
    texto = response.text

    # Si la contraseña es incorrecta, se registra el error
    if texto == "Contraseña incorrecta":
        mensaje = "Error porque la contraseña es incorrecta al autorizar la requisición."
        req_requisicion.autorizo_efirma_error = mensaje
        req_requisicion.save()
        bitacora.error(mensaje)
        raise MyRequestError(mensaje)

    # Convertir el texto a un diccionario
    texto = response.text.replace('"{', "{").replace('}"', "}")
    try:
        _ = json.loads(texto)
    except json.JSONDecodeError:
        mensaje = "Error al cancelar autorización de la requisición porque la respuesta no es JSON."
        req_requisicion.autorizo_efirma_error = mensaje
        req_requisicion.save()
        bitacora.error(mensaje)
        raise MyRequestError(mensaje)

    # Ejemplo de la respuesta
    #   "estatus": "SELLO CANCELADO"
    #   "fechaCancelado": 2022-07-04 12:39:08.0

    # Actualizar la requisición, ahora su estado es CANCELADO POR AUTORIZANTE
    req_requisicion.estado = "CANCELADO POR AUTORIZANTE"
    req_requisicion.autorizo_cancelo_tiempo = datetime.now()
    req_requisicion.autorizo_cancelo_motivo = safe_string(motivo, to_uppercase=False)
    req_requisicion.autorizo_cancelo_error = ""
    req_requisicion.save()

    # Terminar tarea
    mensaje_final = f"Requisición {req_requisicion_id} cancelada su atutorización"
    set_task_progress(progress=100, message=mensaje_final)
    bitacora.info(mensaje_final)
    return mensaje_final


def revisar(req_requisicion_id: int, usuario_id: int, contrasena: str):
    """Firmar electronicamente la requisición por quien revisa"""

    # Validar configuracion
    if REQ_REQUISICIONES_EFIRMA_SER_FIRMA_CADENA_URL is None:
        mensaje = "Falta configurar REQ_REQUISICIONES_EFIRMA_SER_FIRMA_CADENA_URL"
        bitacora.error(mensaje)
        return set_task_error(mensaje)
    if REQ_REQUISICIONES_EFIRMA_QR_URL is None:
        mensaje = "Falta configurar REQ_REQUISICIONES_EFIRMA_QR_URL"
        bitacora.error(mensaje)
        return set_task_error(mensaje)
    if REQ_REQUISICIONES_EFIRMA_APP_ID is None:
        mensaje = "Falta configurar REQ_REQUISICIONES_EFIRMA_APP_ID"
        bitacora.error(mensaje)
        return set_task_error(mensaje)
    if REQ_REQUISICIONES_EFIRMA_APP_PASS is None:
        mensaje = "Falta configurar REQ_REQUISICIONES_EFIRMA_APP_PASS"
        bitacora.error(mensaje)
        return set_task_error(mensaje)

    # Consultar la requisición
    req_requisicion = ReqRequisicion.query.get(req_requisicion_id)
    if req_requisicion is None:
        mensaje = f"No se encontró la requisición {req_requisicion_id}"
        bitacora.error(mensaje)
        return set_task_error(mensaje)
    if req_requisicion.estatus != "A":
        mensaje = f"La requisición {req_requisicion_id} esta eliminada"
        bitacora.error(mensaje)
        return set_task_error(mensaje)
    if req_requisicion.estado != "AUTORIZADO":
        mensaje = f"La requisición {req_requisicion_id} no está en estado AUTORIZADO"
        bitacora.error(mensaje)
        return set_task_error(mensaje)

    # Consultar el usuario que revisa
    revisa = Usuario.query.get(usuario_id)
    if revisa is None:
        mensaje = f"No se encontró el usuario {usuario_id} que revisa"
        bitacora.error(mensaje)
        return set_task_error(mensaje)
    if revisa.efirma_registro_id is None or revisa.efirma_registro_id == 0:
        mensaje = f"El usuario {revisa.email} no tiene registro en el motor de firma"
        bitacora.error(mensaje)
        return set_task_error(mensaje)

    # Juntar los elementos de la requisición para armar la cadena
    elementos = {
        "id": req_requisicion.id,
        "autorizo_nombre": revisa.nombre,
        "autorizo_puesto": revisa.puesto,
        "autorizo_email": revisa.email,
        "creado": req_requisicion.creado.strftime("%Y-%m-%d %H:%M:%S"),
        "solicito_nombre": req_requisicion.solicito_nombre,
        "solicito_puesto": req_requisicion.solicito_puesto,
        "solicito_email": req_requisicion.solicito_email,
    }

    # Preparar los datos que se van a enviar al motor de firma
    data = {
        "cadenaOriginal": json.dumps(elementos),
        "idRegistro": revisa.efirma_registro_id,
        "contrasenaRegistro": contrasena,
        "idAplicacion": REQ_REQUISICIONES_EFIRMA_APP_ID,
        "contrasenaAplicacion": REQ_REQUISICIONES_EFIRMA_APP_PASS,
        "referencia": req_requisicion_id,
        "verificarUrl": True,
    }

    # Enviar la autorizacion al motor de firma
    try:
        response = requests.post(
            REQ_REQUISICIONES_EFIRMA_SER_FIRMA_CADENA_URL,
            data=data,
            timeout=TIMEOUT,
            verify=False,
        )
        response.raise_for_status()
    except requests.exceptions.ConnectionError as error:
        mensaje = "Error de conexion al revisar la requisición." + safe_string(str(error))
        req_requisicion.reviso_efirma_error = mensaje
        req_requisicion.save()
        bitacora.error(mensaje)
        return set_task_error(mensaje)
    except requests.exceptions.HTTPError as error:
        mensaje = "Error porque la respuesta no tiene el estado 200 al revisar la requisición. " + safe_string(str(error))
        req_requisicion.reviso_efirma_error = mensaje
        req_requisicion.save()
        bitacora.error(mensaje)
        return set_task_error(mensaje)
    except requests.exceptions.RequestException as error:
        mensaje = "Error desconocido al revisar la requisición. " + safe_string(str(error))
        req_requisicion.reviso_efirma_error = mensaje
        req_requisicion.save()
        bitacora.error(mensaje)
        return set_task_error(mensaje)

    # Tomar el texto de la respuesta
    texto = response.text

    # Si la contraseña es incorrecta, se registra el error
    if texto == "Contraseña incorrecta":
        mensaje = "Error porque la contraseña es incorrecta al revisar la requsición."
        req_requisicion.reviso_efirma_error = mensaje
        req_requisicion.save()
        bitacora.error(mensaje)
        return set_task_error(mensaje)

    # Convertir el texto a un diccionario
    texto = response.text.replace('"{', "{").replace('}"', "}")
    try:
        datos = json.loads(texto)
    except json.JSONDecodeError:
        mensaje = "Error al revisar la requisición porque la respuesta no es JSON."
        req_requisicion.reviso_efirma_error = mensaje
        req_requisicion.save()
        bitacora.error(mensaje)
        return set_task_error(mensaje)

    # Si el motor de firma entrega "success" en false, se registra el error
    if datos["success"] is False:
        mensaje = "Error al revisar la requisición con este mensaje: " + str(datos["mensaje"])
        req_requisicion.reviso_efirma_error = mensaje
        req_requisicion.save()
        bitacora.error(mensaje)
        return set_task_error(mensaje)

    # Actualizar la requisición, ahora su estado es REVISADO
    req_requisicion.reviso_nombre = revisa.nombre
    req_requisicion.reviso_puesto = revisa.puesto
    req_requisicion.reviso_email = revisa.email
    req_requisicion.reviso_efirma_tiempo = datetime.strptime(datos["fecha"], "%d/%m/%Y %H:%M:%S")
    req_requisicion.reviso_efirma_folio = datos["folio"]
    req_requisicion.reviso_efirma_sello_digital = datos["selloDigital"]
    req_requisicion.reviso_efirma_url = datos["url"]
    req_requisicion.reviso_efirma_qr_url = f"{REQ_REQUISICIONES_EFIRMA_QR_URL}?size=300&qrtext={datos['url']}"
    req_requisicion.reviso_efirma_mensaje = datos["mensaje"]
    req_requisicion.reviso_efirma_error = ""
    req_requisicion.estado = "REVISADO"
    req_requisicion.save()

    # Terminar tarea
    mensaje_final = f"Requisición {req_requisicion.glosa} revisada"
    set_task_progress(progress=100, message=mensaje_final)
    bitacora.info(mensaje_final)
    return mensaje_final


def cancelar_revisar(req_requisicion_id: int, contrasena: str, motivo: str):
    """Cancelar la firma electronica de una requisición por quien revisa"""

    # Validar configuracion
    if REQ_REQUISICIONES_EFIRMA_CAN_FIRMA_CADENA_URL is None:
        mensaje = "Falta configurar REQ_REQUISICIONES_EFIRMA_CAN_FIRMA_CADENA_URL"
        bitacora.error(mensaje)
        raise MyMissingConfigurationError(mensaje)
    if REQ_REQUISICIONES_EFIRMA_APP_ID is None:
        mensaje = "Falta configurar REQ_REQUISICIONES_EFIRMA_APP_ID"
        bitacora.error(mensaje)
        raise MyMissingConfigurationError(mensaje)
    if REQ_REQUISICIONES_EFIRMA_APP_PASS is None:
        mensaje = "Falta configurar REQ_REQUISICIONES_EFIRMA_APP_PASS"
        bitacora.error(mensaje)
        raise MyMissingConfigurationError(mensaje)

    # Consultar la requisición
    req_requisicion = ReqRequisicion.query.get(req_requisicion_id)
    if req_requisicion is None:
        mensaje = f"No se encontró la requisición {req_requisicion_id}"
        bitacora.error(mensaje)
        raise MyNotValidParamError(mensaje)
    if req_requisicion.estatus != "A":
        mensaje = f"La requisición {req_requisicion_id} esta eliminada"
        bitacora.error(mensaje)
        raise MyNotValidParamError(mensaje)
    if req_requisicion.estado != "REVISADO":
        mensaje = f"La requisición {req_requisicion_id} no está en estado REVISADO"
        bitacora.error(mensaje)
        raise MyNotValidParamError(mensaje)
    if req_requisicion.reviso_efirma_folio is None:
        mensaje = f"La requisición {req_requisicion_id} no tiene folio de revisado"
        bitacora.error(mensaje)
        raise MyNotValidParamError(mensaje)

    # Consultar el usuario que revisa, para cancelar la firma
    revisa = Usuario.query.filter_by(email=req_requisicion.reviso_email).first()
    if revisa is None:
        mensaje = f"No se encontró el usuario {req_requisicion.reviso_email} que revisa"
        bitacora.error(mensaje)
        raise MyNotValidParamError(mensaje)
    if revisa.efirma_registro_id is None or revisa.efirma_registro_id == 0:
        mensaje = f"El usuario {req_requisicion.reviso_email} no tiene registro en el motor de firma"
        bitacora.error(mensaje)
        raise MyNotValidParamError(mensaje)
    if ROL_REVISANTES not in revisa.get_roles():
        mensaje = f"El usuario {revisa.email} no tiene el rol {ROL_REVISANTES}"
        bitacora.error(mensaje)
        raise MyNotValidParamError(mensaje)

    # Preparar los datos que se van a enviar al motor de firma
    data = {
        "idAplicacion": REQ_REQUISICIONES_EFIRMA_APP_ID,
        "contrasenaAplicacion": REQ_REQUISICIONES_EFIRMA_APP_PASS,
        "idRegistro": revisa.efirma_registro_id,
        "contrasenaRegistro": contrasena,
        "folios": req_requisicion.reviso_efirma_folio,
    }

    # Enviar la cancelacion al motor de firma
    try:
        response = requests.post(
            REQ_REQUISICIONES_EFIRMA_CAN_FIRMA_CADENA_URL,
            data=data,
            timeout=TIMEOUT,
            verify=False,
        )
        response.raise_for_status()
    except requests.exceptions.ConnectionError as error:
        mensaje = "Error de conexion al cancelar la requisición. " + safe_string(str(error))
        req_requisicion.reviso_efirma_error = mensaje
        req_requisicion.save()
        bitacora.error(mensaje)
        raise MyConnectionError(mensaje)
    except requests.exceptions.HTTPError as error:
        mensaje = "Error porque la respuesta no tiene el estado 200 al cancelar la requisición. " + safe_string(str(error))
        req_requisicion.reviso_efirma_error = mensaje
        req_requisicion.save()
        bitacora.error(mensaje)
        raise MyStatusCodeError(mensaje)
    except requests.exceptions.RequestException as error:
        mensaje = "Error desconocido al cancelar la requisición. " + safe_string(str(error))
        req_requisicion.reviso_efirma_error = mensaje
        req_requisicion.save()
        bitacora.error(mensaje)
        raise MyRequestError(mensaje)

    # Tomar el texto de la respuesta
    texto = response.text

    # Si la contraseña es incorrecta, se registra el error
    if texto == "Contraseña incorrecta":
        mensaje = "Error porque la contraseña es incorrecta al revisar la requisición."
        req_requisicion.reviso_efirma_error = mensaje
        req_requisicion.save()
        bitacora.error(mensaje)
        raise MyRequestError(mensaje)

    # Convertir el texto a un diccionario
    texto = response.text.replace('"{', "{").replace('}"', "}")
    try:
        _ = json.loads(texto)
    except json.JSONDecodeError:
        mensaje = "Error al cancelar revisión de la requisición porque la respuesta no es JSON."
        req_requisicion.reviso_efirma_error = mensaje
        req_requisicion.save()
        bitacora.error(mensaje)
        raise MyRequestError(mensaje)

    # Ejemplo de la respuesta
    #   "estatus": "SELLO CANCELADO"
    #   "fechaCancelado": 2022-07-04 12:39:08.0

    # Actualizar la requisición, ahora su estado es CANCELADO POR AUTORIZANTE
    req_requisicion.estado = "CANCELADO POR REVISANTE"
    req_requisicion.reviso_cancelo_tiempo = datetime.now()
    req_requisicion.reviso_cancelo_motivo = safe_string(motivo, to_uppercase=False)
    req_requisicion.reviso_cancelo_error = ""
    req_requisicion.save()

    # Terminar tarea
    mensaje_final = f"Requisición {req_requisicion_id} cancelada su revisión"
    set_task_progress(progress=100, message=mensaje_final)
    bitacora.info(mensaje_final)
    return mensaje_final