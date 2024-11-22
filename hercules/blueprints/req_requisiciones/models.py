"""
Requisiciones , modelos
"""

from collections import OrderedDict
from hercules.extensions import database
from lib.universal_mixin import UniversalMixin


class ReqRequisicion(database.Model, UniversalMixin):
    """ReqRequision"""

    ESTADOS = OrderedDict(
        [
            ("CREADO", "Creado"),  # PASO 1
            ("SOLICITADO", "Solicitado"),  # PASO 2
            ("CANCELADO POR SOLICITANTE", "Cancelado por solicitante"),  #
            ("AUTORIZADO", "Autorizado"),  # PASO 3
            ("CANCELADO POR AUTORIZANTE", "Cancelado por autorizante"),  #
            ("REVISADO", "Revisado"),  # PASO 4
            ("CANCELADO POR REVISANTE", "Cancelado por revisante"),  #
        ]
    )

    # Nombre de la tabla
    __tablename__ = "req_requisiciones"

    # Clave primaria
    id = database.Column(database.Integer, primary_key=True)

    # Claves foráneas
    autoridad_id = database.Column(database.Integer, database.ForeignKey("autoridades.id"), index=True, nullable=False)
    autoridad = database.relationship("Autoridad", back_populates="req_requisiciones")
    usuario_id = database.Column(database.Integer, database.ForeignKey("usuarios.id"), index=True, nullable=False)
    usuario = database.relationship("Usuario", back_populates="req_requisiciones")

    # Columnas
    fecha = database.Column(database.Date, nullable=False)
    consecutivo = database.Column(database.String(30), nullable=False)
    observaciones = database.Column(database.Text())
    estado = database.Column(
        database.Enum(*ESTADOS, name="estados", native_enum=False),
        index=True,
        nullable=False,
        default="CREADO",
        server_default="CREADO",
    )
    glosa = database.Column(database.String(30))
    programa = database.Column(database.String(60))
    fuente = database.Column(database.String(50))
    area = database.Column(database.String(100))
    fecha_requerida = database.Column(database.Date)
    justificacion = database.Column(database.Text())

    # Columnas estado SOLICITADO
    solicito_nombre = database.Column(database.String(256))
    solicito_puesto = database.Column(database.String(256))
    solicito_email = database.Column(database.String(256))
    solicito_efirma_tiempo = database.Column(database.DateTime)
    solicito_efirma_folio = database.Column(database.Integer)
    solicito_efirma_sello_digital = database.Column(database.String(512))
    solicito_efirma_url = database.Column(database.String(256))
    solicito_efirma_qr_url = database.Column(database.String(256))
    solicito_efirma_mensaje = database.Column(database.String(512))
    solicito_efirma_error = database.Column(database.String(512))

    # Columnas estado CANCELADO POR SOLICITANTE
    solicito_cancelo_tiempo = database.Column(database.DateTime)
    solicito_cancelo_motivo = database.Column(database.String(256))
    solicito_cancelo_error = database.Column(database.String(512))

    # Columnas estado AUTORIZADO
    autorizo_nombre = database.Column(database.String(256))
    autorizo_puesto = database.Column(database.String(256))
    autorizo_email = database.Column(database.String(256))
    autorizo_efirma_tiempo = database.Column(database.DateTime)
    autorizo_efirma_folio = database.Column(database.Integer)
    autorizo_efirma_sello_digital = database.Column(database.String(512))
    autorizo_efirma_url = database.Column(database.String(256))
    autorizo_efirma_qr_url = database.Column(database.String(256))
    autorizo_efirma_mensaje = database.Column(database.String(512))
    autorizo_efirma_error = database.Column(database.String(512))

    # Columnas estado CANCELADO POR AUTORIZANTE
    autorizo_cancelo_tiempo = database.Column(database.DateTime)
    autorizo_cancelo_motivo = database.Column(database.String(256))
    autorizo_cancelo_error = database.Column(database.String(512))

    # Columnas (step 3 authorize) estado AUTORIZADO
    reviso_nombre = database.Column(database.String(256))
    reviso_puesto = database.Column(database.String(256))
    reviso_email = database.Column(database.String(256))
    reviso_efirma_tiempo = database.Column(database.DateTime)
    reviso_efirma_folio = database.Column(database.Integer)
    reviso_efirma_sello_digital = database.Column(database.String(512))
    reviso_efirma_url = database.Column(database.String(256))
    reviso_efirma_qr_url = database.Column(database.String(256))
    reviso_efirma_mensaje = database.Column(database.String(512))
    reviso_efirma_error = database.Column(database.String(512))

    # Columnas estado CANCELADO POR AUTORIZANTE
    reviso_cancelo_tiempo = database.Column(database.DateTime)
    reviso_cancelo_motivo = database.Column(database.String(256))
    reviso_cancelo_error = database.Column(database.String(512))

    # Hijos
    req_resguardos = database.relationship("ReqResguardo", back_populates="req_requisicion")
    req_requisiciones_registros = database.relationship("ReqRequisicionRegistro", back_populates="req_requisicion")

    def __repr__(self):
        """Representación"""
        return f"<ReqRequision {self.id}>"
