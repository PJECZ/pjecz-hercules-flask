"""
Conversions, convertir a PDF
"""

from datetime import datetime
from io import BytesIO
import os

from dotenv import load_dotenv
from xhtml2pdf import pisa

from hercules.app import create_app
from hercules.blueprints.req_requisiciones.conversions import bitacora
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
CLOUD_STORAGE_DEPOSITO_REQUISICIONES = os.getenv("CLOUD_STORAGE_DEPOSITO_REQUISICIONES", "")

# Cargar la aplicación para tener acceso a la base de datos
app = create_app()
app.app_context().push()
database.app = app


def convertir_a_pdf(req_requisicion_id: str) -> tuple[str, str, str]:
    """Convertir a PDF"""

    mensajes = []
    mensaje_info = f"Inicia convertir a PDF {req_requisicion_id}."
    mensajes.append(mensaje_info)
    bitacora.info(mensaje_info)

    # Validar que esté definida la variable de entorno CLOUD_STORAGE_DEPOSITO_REQUISICIONES
    if not CLOUD_STORAGE_DEPOSITO_REQUISICIONES:
        error = "La variable de entorno CLOUD_STORAGE_DEPOSITO_REQUISICIONES no está definida"
        bitacora.error(error)
        raise MyNotValidParamError(error)

    # Consultar la requisición
    req_requisicion_id = safe_uuid(req_requisicion_id)
    if not req_requisicion_id:
        error = "ID de Requisición inválido"
        bitacora.error(error)
        raise MyNotValidParamError(error)
    
    req_requisicion = ReqRequisicion.query.get(req_requisicion_id)
    articulos = database.session.query(ReqRequisicionRegistro, ReqCatalogo).filter_by(req_requisicion_id=req_requisicion_id, estatus="A" ).join(ReqCatalogo).all()
    usuario = Usuario.query.get_or_404(req_requisicion.usuario_id)
    
    usuario_solicito = None
    usuario_autorizo = None
    usuario_reviso = None

    usuario_solicito_nombre = ''
    autoridad_solicito_descripcion = ''
    usuario_autorizo_nombre = ''
    autoridad_autorizo_descripcion = ''
    usuario_reviso_nombre = ''
    autoridad_reviso_descripcion = ''

    if req_requisicion.solicito_id!=0 :
        usuario_solicito = Usuario.query.get_or_404(req_requisicion.solicito_id)
        usuario_solicito_nombre = usuario_solicito.nombre
        autoridad_solicito = Autoridad.query.get_or_404(usuario_solicito.autoridad_id)
        autoridad_solicito_descripcion = autoridad_solicito.descripcion

    if req_requisicion.autorizo_id!=0 :
        usuario_autorizo = Usuario.query.get_or_404(req_requisicion.autorizo_id)
        usuario_autorizo_nombre = usuario_autorizo.nombre
        autoridad_autorizo = Autoridad.query.get_or_404(usuario_autorizo.autoridad_id)
        autoridad_autorizo_descripcion = autoridad_autorizo.descripcion
    
    if req_requisicion.reviso_id!=0 :
        usuario_reviso = Usuario.query.get_or_404(req_requisicion.reviso_id)
        usuario_reviso_nombre = usuario_reviso.nombre
        autoridad_reviso = Autoridad.query.get_or_404(usuario_reviso.autoridad_id)
        autoridad_reviso_descripcion = autoridad_reviso.descripcion

    
    
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

    articulos = (
        database.session.query(ReqRequisicionRegistro, ReqCatalogo)
        .filter_by(req_requisicion_id=req_requisicion_id, estatus="A")
        .join(ReqCatalogo)
        .all()
    )

    usuario_solicito = None
    usuario_autorizo = None
    usuario_reviso = None

    usuario_solicito_nombre = ""
    autoridad_solicito_descripcion = ""
    usuario_autorizo_nombre = ""
    autoridad_autorizo_descripcion = ""
    usuario_reviso_nombre = ""
    autoridad_reviso_descripcion = ""

    if req_requisicion.solicito_id != 0:
        usuario_solicito = Usuario.query.get(req_requisicion.solicito_id)
        usuario_solicito_nombre = usuario_solicito.nombre
        autoridad_solicito = Autoridad.query.get(usuario_solicito.autoridad_id)
        autoridad_solicito_descripcion = autoridad_solicito.descripcion

    if req_requisicion.autorizo_id != 0:
        usuario_autorizo = Usuario.query.get(req_requisicion.autorizo_id)
        usuario_autorizo_nombre = usuario_autorizo.nombre
        autoridad_autorizo = Autoridad.query.get(usuario_autorizo.autoridad_id)
        autoridad_autorizo_descripcion = autoridad_autorizo.descripcion

    if req_requisicion.reviso_id != 0:
        usuario_reviso = Usuario.query.get(req_requisicion.reviso_id)
        usuario_reviso_nombre = usuario_reviso.nombre
        autoridad_reviso = Autoridad.query.get(usuario_reviso.autoridad_id)
        autoridad_reviso_descripcion = autoridad_reviso.descripcion

    #
    # Convertir el contenido HTML a archivo PDF
    #

    # Iniciar el contenido del archivo PDF
    contenidos = []

    contenidos.append("""
        <html>
            <head>
                <style>
                    @page {
                        size: letter portrait;
                        margin: .3in ;
                        @frame footer_frame {
                                -pdf-frame-content: footer_content;
                                left: 50pt;
                                width: 512pt;
                                top: 700pt;
                                height: 50pt;
                                border:1px solid #444;
                                background-color: #efeff1;
                            }
                        }
                </style>
            </head>
    """)
    # Agregar tag html y head
    contenidos.append("<html>")
    contenidos.append("<head>")

    # Agregar el cierre del tag head e iniciar el tag body
    contenidos.append("</head>")
    contenidos.append("<body>")

    # Agregar tag style con el CSS para definir la hoja tamaño carta, la cabecera, el contenido y el pie de página
    contenidos.append(
        f'''
        <body style='width:90%'>
            <div id='footer_content' style='text-align:center'>
                <b>PODER JUDICIAL DEL ESTADO DE COAHUILA DE ZARAGOZA</b><br>
                Dirección de Recursos Materiales<br>
                Blvd. Isidro López Zertuche 2791 Col. Los Maestros<br>
                C.P. 25236 Saltillo, Coahuila, Tel. (844) 438 03 50 Ext. 6991<br>
            </div>

                <table style='width:100%; margin:0 auto;' repeat='1'>
                    <tr>
                        <td><img src='static/img/escudo.png' width='280'></td>
                        <td align='center' style='width:70%'>
                            <h1 style='text-align:center'>REQUISICIÓN</h1>
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
        
                <table style='border:1px solid #666' cellspacing=0 cellpadding=0>
                    <tr>
                        <td>


                            <table border=0 width='100%' cellspacion=0 cellpadding=2 style='margin:0 auto;'>
                                <tr>
                                    <td colspan='6' style='text-align: center; background-color:#ccc; color:#333; font-size:8px'><b>ÁREA SOLICITANTE</b></td>
                                    <td colspan='6' style='text-align: center; background-color:#ccc; color:#333; font-size:8px'><b>GLOSA</td>
                                </tr>
                                <tr>
                                    <td colspan='6' style='text-align:center'>{autoridad_solicito_descripcion}</td>
                                    <td colspan='6' style='text-align:center'>{req_requisicion.glosa}</td>
                                </tr>
                                <tr>
                                    <td colspan='6' style='text-align: center;background-color:#ccc; color:#333; font-size:8px'><b>PROGRAMA</b></td>
                                    <td colspan='6' style='text-align: center;background-color:#ccc; color:#333; font-size:8px'><b>FUENTE DE FINANCIAMIENTO</b></td>
                                </tr>
                                <tr>
                                    <td colspan='6' style='text-align:center'>{req_requisicion.programa}</td>
                                    <td colspan='6' style='text-align:center'>{req_requisicion.fuente_financiamiento}</td>
                                </tr>
                                <tr>
                                    <td colspan='6' style='text-align: center;background-color:#ccc; color:#333; font-size:8px'><b>ÁREA FINAL A QUIEN SE ENTREGARA</b></td>
                                    <td colspan='6' style='text-align: center;background-color:#ccc; color:#333; font-size:8px'><b>FECHA REQUERIDA</b></td>
                                </tr>
                                <tr>
                                    <td colspan='6'></td>
                                    <td colspan='6' style='text-align:center'>{req_requisicion.fecha_requerida}</td>
                                </tr>
                                <tr>
                                    <td colspan='12' style='background-color:#ccc; color:#333; font-size:8px'><b>OBSERVACIONES</b></td>
                                </tr>
                                <tr>
                                    <td colspan='12' style=''>{req_requisicion.observaciones}</td>
                                </tr>
                                <tr>
                                    <td colspan='12' style='background-color:#ccc; color:#333; font-size:8px'><b>JUSTIFICACION</b></td>
                                </tr>
                                <tr>
                                    <td colspan='12' style=''>{req_requisicion.justificacion}</td>
                                </tr>
                                <tr>
                                    <td colspan=3 style='text-align: center;background-color:#ccc; color:#333; font-size:8px'><b>CLAVE</b></td>
                                    <td colspan=5 style='text-align: center;background-color:#ccc; color:#333; font-size:8px'><b>DESCRIPCION</b></td>
                                    <td style='text-align: center;background-color:#ccc; color:#333; font-size:8px'><b>U. MEDIDA</b></td>
                                    <td style='text-align: center;background-color:#ccc; color:#333; font-size:8px'><b>CANTIDAD</b></td>
                                    <td style='text-align: center;background-color:#ccc; color:#333; font-size:8px'><b>CLAVE</b></td>
                                    <td style='text-align: center;background-color:#ccc; color:#333; font-size:8px'><b>DETALLE</b></td>
                                </tr>
    '''
    )

    if articulos: 
        for campos in articulos:
            contenidos.append(            
                f'''
                <tr>
                    <td colspan=3 style='text-align:center'>{campos.ReqCatalogo.codigo}</td>
                    <td colspan=5 style='text-align:center'>{campos.ReqCatalogo.descripcion}</td>
                    <td style='text-align:center'>{campos.ReqCatalogo.unidad_medida}</td>
                    <td style='text-align:center'>{campos.ReqRequisicionRegistro.cantidad}</td>
                    <td style='text-align:center'>{campos.ReqRequisicionRegistro.clave}</td>
                    <td style='text-align:center'>{campos.ReqRequisicionRegistro.detalle}</td>
                </tr>
                '''
                )
    else:
        contenidos.append(
            '''
                <tr>
                    <td colspan=3></td>
                    <td colspan=5></td>
                    <td></td>
                    <td></td>
                    <td></td>
                    <td></td>
                </tr>
            '''
        )
    
    contenidos.append(
        f'''
                        </table>

                    </td>
                </tr>
            </table>

        
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
                        {usuario_solicito_nombre}<br>
                        {autoridad_solicito_descripcion}
                    </td>
                    <td>
                        AUTORIZA
                        <br><br><br><br>
                        ________________________________<br>
                        {usuario_autorizo_nombre}
                        {autoridad_autorizo_descripcion}
                    </td>
                    <td>
                        REVISÓ
                        <br><br><br><br>
                        ________________________________<br>
                        {usuario_reviso_nombre}
                        {autoridad_reviso_descripcion}
                    </td>
                </tr>
            </table>
        
    '''
    )
    contenidos.append('</body>')
    contenidos.append('</html>')


    # Convertir el contenido HTML a archivo PDF
    pdf_buffer = BytesIO()
    _ = pisa.CreatePDF("\n".join(contenidos), dest=pdf_buffer, encoding="UTF-8")
    pdf_buffer.seek(0)
    archivo_pdf_bytes = pdf_buffer.read()

    #
    # Subir a Google Cloud Storage el archivo PDF
    #

    # Definir la ruta para blob_name con la fecha actual
    archivo_pdf_nombre = f"{req_requisicion.id}.pdf"
    fecha_hora_recepcion = datetime.now()
    anio = fecha_hora_recepcion.strftime("%Y")
    mes = fecha_hora_recepcion.strftime("%m")
    dia = fecha_hora_recepcion.strftime("%d")
    blob_name = f"req_requisiciones/{anio}/{mes}/{dia}/{archivo_pdf_nombre}"

    # Subir el archivo en Google Storage
    try:
        archivo_pdf_url = upload_file_to_gcs(
            bucket_name=CLOUD_STORAGE_DEPOSITO_REQUISICIONES,
            blob_name=blob_name,
            content_type="application/pdf",
            data=archivo_pdf_bytes,
        )
    except (MyBucketNotFoundError, MyUploadError) as error:
        bitacora.error(f"Error al subir el archivo PDF a Google Cloud Storage: {error}")
        raise error

    # Actualizar el documento con la URL del archivo PDF
    req_requisicion.archivo_pdf_url = archivo_pdf_url
    req_requisicion.save()

    # Elaborar mensaje_termino
    mensaje_termino = "Termina convertir a PDF."
    mensajes.append(mensaje_termino)
    bitacora.info(mensaje_termino)

    # Entregar mensaje_termino, nombre_archivo y url_publica
    return "\n".join(mensajes), archivo_pdf_nombre, archivo_pdf_url
