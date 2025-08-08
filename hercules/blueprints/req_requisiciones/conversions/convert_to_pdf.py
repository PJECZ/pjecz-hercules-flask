"""
Conversions, convertir a PDF
"""

from datetime import datetime
import os
import logging

from dotenv import load_dotenv
from xhtml2pdf import pisa

from hercules.app import create_app
from hercules.blueprints.req_requisiciones.models import ReqRequisicion
from hercules.extensions import database
from lib.exceptions import MyBucketNotFoundError, MyIsDeletedError, MyNotExistsError, MyNotValidParamError, MyUploadError
from lib.google_cloud_storage import upload_file_to_gcs
from lib.safe_string import safe_uuid
from hercules.extensions import database
from hercules.blueprints.autoridades.models import Autoridad
from hercules.blueprints.req_catalogos.models import ReqCatalogo
from hercules.blueprints.req_requisiciones_registros.models import ReqRequisicionRegistro
from hercules.blueprints.usuarios.models import Usuario

# Cargar variables de entorno
load_dotenv()
CLOUD_STORAGE_DEPOSITO_OFICIOS = os.getenv("CLOUD_STORAGE_DEPOSITO_OFICIOS", "")

# Cargar la bitácora
bitacora = logging.getLogger(__name__)
bitacora.setLevel(logging.INFO)
formato = logging.Formatter("%(asctime)s:%(levelname)s:%(message)s")
empunadura = logging.FileHandler("logs/cid_formatos.log")
empunadura.setFormatter(formato)
bitacora.addHandler(empunadura)

# Cargar la aplicación para tener acceso a la base de datos
app = create_app()
app.app_context().push()
database.app = app


def convertir_a_pdf(req_requisicion_id: str) -> tuple[str, str, str]:
    """Convertir a PDF"""

    print("******************* Inicia la conversion ********************************")
    print(req_requisicion_id)
    mensajes = []
    mensaje_info = "Inicia convertir a PDF."
    mensajes.append(mensaje_info)
    bitacora.info(mensaje_info)

    # Validar que esté definida la variable de entorno CLOUD_STORAGE_DEPOSITO_OFICIOS
    #    if not CLOUD_STORAGE_DEPOSITO_OFICIOS:
    #        error = "La variable de entorno CLOUD_STORAGE_DEPOSITO_OFICIOS no está definida"
    #        bitacora.error(error)
    #        raise MyNotValidParamError(error)

    # Consultar el oficio
    req_requisicion_id = safe_uuid(req_requisicion_id)
    if not req_requisicion_id:
        error = "ID de Requisición inválido"
        bitacora.error(error)
        raise MyNotValidParamError(error)

    req_requisicion = ReqRequisicion.query.get(req_requisicion_id)
    articulos = (
        database.session.query(ReqRequisicionRegistro, ReqCatalogo)
        .filter_by(req_requisicion_id=req_requisicion_id)
        .join(ReqCatalogo)
        .all()
    )
    usuario = Usuario.query.get_or_404(req_requisicion.usuario_id)
    usuario_solicito = Usuario.query.get_or_404(req_requisicion.solicito_id) if req_requisicion.solicito_id != "" else ""
    usuario_autorizo = Usuario.query.get_or_404(req_requisicion.autorizo_id) if req_requisicion.autorizo_id != "" else ""
    usuario_reviso = Usuario.query.get_or_404(req_requisicion.reviso_id) if req_requisicion.reviso_id != "" else ""
    autoridad = Autoridad.query.get_or_404(req_requisicion.usuario.autoridad_id)

    if not req_requisicion:
        error = "La requisición no existe"
        bitacora.error(error)
        raise MyNotExistsError(error)

    # Validar el estatus, que no esté eliminada
    if req_requisicion.estatus != "A":
        error = "La Requisición está eliminada"
        bitacora.error(error)
        raise MyIsDeletedError(error)

    # Validar que el estado sea FIRMADO
    if req_requisicion.estado not in ["SOLICITADO", "AUTORIZADO", "REVISADO"]:
        error = "La requisición no tiene la FIRMA SIMPLE"
        bitacora.error(error)
        raise MyNotValidParamError(error)

    # Validar que archivo_pdf_url sea None
    if req_requisicion.archivo_pdf_url:
        error = "La requisición ya tiene un archivo PDF asociado."
        bitacora.error(error)
        raise MyNotValidParamError(error)

    #
    # Convertir el contenido HTML a archivo PDF
    #

    # Iniciar el contenido del archivo PDF
    contenidos = []

    # Agregar tag html y head

    contenidos.append(
        f"""
    <html>
        <head>
        </head>
        <body>

            <table style='width:100%; margin:0 auto;' repeat='1'>
                <tr>
                    <td><img src='static/img/escudo.jpg' width='280'></td>
                    <td align='center' style='width:70%'>
                        <b>PODER JUDICIAL DEL ESTADO DE COAHUILA DE ZARAGOZA</b>
                        <br>
                        Dirección de Recursos Materiales<br>
                        Blvd. Isidro López Zertuche 2791 Col. Los Maestros<br>
                        C.P. 25236 Saltillo, Coahuila, Tel. (844) 438 03 50 Ext. 6991<br>
                    </td>
                    <td style='text-align:right'>

                        <table border='1' cellpadding='2' cellspacing='0' style='text-align:center; width:50%'>
                            <tr>
                                <td style='background-color:#ccc'>FECHA</td>
                            </tr>
                            <tr>
                                <td>{req_requisicion.creado}</td>
                            </tr>
                            <tr>
                                <td style='background-color:#ccc'>GASTO</td>
                            </tr>
                            <tr>
                                <td>{ req_requisicion.gasto }</td>
                            </tr>
                        </table>
                    </td>
                </tr>
            </table>
    
            <h1 style='text-align:center'>Requisición</h1>
            <table border=0 width='100%' cellspacion=0 cellpadding=2 style='margin:0 auto'>
                <tr>
                    <td colspan='6' style='background-color:#efeff1; color:#333'>ÁREA SOLICITANTE</td>
                    <td colspan='6' style='background-color:#efeff1; color:#333'>GLOSA</td>
                </tr>
                <tr>
                    <td colspan='6'>{autoridad.descripcion}</td>
                    <td colspan='6'>{req_requisicion.glosa}</td>
                </tr>
                <tr>
                    <td colspan='6' style='background-color:#efeff1; color:#333'>PROGRAMA</td>
                    <td colspan='6' style='background-color:#efeff1; color:#333'>FUENTE DE FINANCIAMIENTO</td>
                </tr>
                <tr>
                    <td colspan='6'>{req_requisicion.programa}</td>
                    <td colspan='6'>{req_requisicion.fuente_financiamiento}</td>
                </tr>
                <tr>
                    <td colspan='6' style='background-color:#efeff1; color:#333'>ÁREA FINAL A QUIEN SE ENTREGARA</td>
                    <td colspan='6' style='background-color:#efeff1; color:#333'>FECHA REQUERIDA</td>
                </tr>
                <tr>
                    <td colspan='6'></td>
                    <td colspan='6'>{req_requisicion.fecha_requerida}</td>
                </tr>
                <tr>
                    <td colspan='12' style='background-color:#efeff1; color:#333'>OBSERVACIONES</td>
                </tr>
                <tr>
                    <td colspan='12'>{req_requisicion.observaciones}</td>
                </tr>
                <tr>
                    <td colspan='12' style='background-color:#efeff1; color:#333'>JUSTIFICACION</td>
                </tr>
                <tr>
                    <td colspan='12'>{req_requisicion.justificacion}</td>
                </tr>
                <tr>
                    <td colspan=3 style='background-color:#ccc; color:#333'>CLAVE</td>
                    <td colspan=5 style='background-color:#ccc; color:#333'>DESCRIPCION</td>
                    <td style='background-color:#ccc; color:#333'>U. MEDIDA</td>
                    <td style='background-color:#ccc; color:#333'>CANTIDAD</td>
                    <td style='background-color:#ccc; color:#333'>CLAVE</td>
                    <td style='background-color:#ccc; color:#333'>DETALLE</td>
                </tr>
    """
    )

    if articulos:
        for campos in articulos:
            contenidos.append(
                f"""
                <tr>
                    <td colspan=3>{campos.ReqCatalogo.id}</td>
                    <td colspan=5>{campos.ReqCatalogo.descripcion}</td>
                    <td>{campos.ReqCatalogo.unidad_medida}</td>
                    <td>{campos.ReqRequisicionRegistro.cantidad}</td>
                    <td>{campos.ReqCatalogo.clave}</td>
                    <td></td>
                </tr>
                """
            )
    else:
        contenidos.append(
            """
                <tr>
                    <td colspan=3></td>
                    <td colspan=5></td>
                    <td></td>
                    <td></td>
                    <td></td>
                    <td></td>
                </tr>
            """
        )

    contenidos.append(
        f"""
            </table>
        </div>
        
        <div class='row container' style='width: 70%;'>
        </div>
        <div style='font-family:helvetica;'>
            <table style='width:70%;  margin: 0 auto; text-align:center'>
                <tr>
                    <td colspan='3'><br>
                        <hr style='border: double'><br>
                        <label><b>Firma Simple: </b></label>
                        <label>{req_requisicion.firma_simple}</label>
                        <hr style='border: double'><br>
                    </td>
                </tr>
                <tr>
                    <td>
                        SOLICITA
                        <br><br><br>
                        <br>
                        ________________________________<br>
                        {usuario_solicito.nombres} {usuario_solicito.apellido_paterno} {usuario_solicito.apellido_materno}<br>
                        {autoridad.descripcion}
                    </td>
                    <td>
                        AUTORIZA
                        <br><br><br><br>
                        ________________________________<br>
                        {usuario_autorizo.nombres} {usuario_autorizo.apellido_paterno} {usuario_autorizo.apellido_materno}
                    </td>
                    <td>
                        REVISÓ
                        <br><br><br><br>
                        ________________________________<br>
                        {usuario_reviso.nombres} {usuario_reviso.apellido_paterno} {usuario_reviso.apellido_materno}
                    </td>
                </tr>
            </table>
        </div>
        <br>
        <br>

        </body>
    </html>
    """
    )

    # Convertir el contenido HTML a archivo PDF
    archivo = req_requisicion.gasto + ".pdf"
    with open("./hercules/blueprints/req_requisiciones/documentos/" + archivo, "w+b") as result_file:
        pisa_status = pisa.CreatePDF("\n".join(contenidos), dest=result_file, encoding="UTF-8")

    # archivo_pdf = pisa.CreatePDF("\n".join(contenidos), dest_bytes=True, encoding="UTF-8")

    #
    # Subir a Google Cloud Storage el archivo PDF
    #

    # Definir la ruta para blob_name con la fecha actual
    archivo_pdf_nombre = f"{req_requisicion.id}.pdf"
    fecha_hora_recepcion = datetime.now()
    anio = fecha_hora_recepcion.strftime("%Y")
    mes = fecha_hora_recepcion.strftime("%m")
    dia = fecha_hora_recepcion.strftime("%d")
    blob_name = f"ofi_documentos/{anio}/{mes}/{dia}/{archivo_pdf_nombre}"

    archivo_pdf_url = "url/temporal/del/archivo.pdf"

    # Subir el archivo en Google Storage
    #    try:
    #        archivo_pdf_url = upload_file_to_gcs(
    #            bucket_name=CLOUD_STORAGE_DEPOSITO_OFICIOS,
    #            blob_name=blob_name,
    #            content_type="application/pdf",
    #            data=archivo_pdf,
    #        )
    #    except (MyBucketNotFoundError, MyUploadError) as error:
    #        bitacora.error(f"Error al subir el archivo PDF a Google Cloud Storage: {error}")
    #        raise error

    # Actualizar el oficio con la URL del archivo PDF
    #    req_requisicion.archivo_pdf_url = archivo_pdf_url
    #    req_requisicion.save()

    # Elaborar mensaje_termino
    mensaje_termino = "Termina convertir a PDF."
    mensajes.append(mensaje_termino)
    bitacora.info(mensaje_termino)

    print("******************* termino la conversion ********************************")
    print(req_requisicion_id)

    # Entregar mensaje_termino, nombre_archivo y url_publica
    return "\n".join(mensajes), archivo_pdf_nombre, archivo_pdf_url
