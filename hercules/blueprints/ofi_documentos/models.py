"""
Ofi Documentos, modelos
"""

from datetime import datetime
from typing import List, Optional

from sqlalchemy import Enum, ForeignKey, String, Text
from sqlalchemy.orm import Mapped, mapped_column, relationship

from lib.universal_mixin import UniversalMixin
from hercules.extensions import database


class OfiDocumento(database.Model, UniversalMixin):
    """ OfiDocumento """

    ESTADOS = {
        "BORRADOR": "Borrador",
        "FIRMADO": "Firmado",
        "ENVIADO": "Enviado",
        "CANCELADO": "Cancelado",
    }

    # Nombre de la tabla
    __tablename__ = 'ofi_documentos'

    # Clave primaria
    id: Mapped[int] = mapped_column(primary_key=True)

    # Clave foránea
    usuario_id: Mapped[int] = mapped_column(ForeignKey("usuarios.id"))
    usuario: Mapped["Usuario"] = relationship(back_populates="ofi_documentos")

    # Columnas
    descripcion: Mapped[str] = mapped_column(String(256))
    contenido: Mapped[str] = mapped_column(Text)
    estado: Mapped[str] = mapped_column(Enum(*ESTADOS, name="ofi_documentos_estados", native_enum=False), index=True)
    folio: Mapped[Optional[int]]  # En BORRADOR puede ser None
    firmante_usuario_id: Mapped[Optional[int]]
    es_archivado: Mapped[bool] = mapped_column(default=False)
    firma_simple: Mapped[str] = mapped_column(String(256), default="")

    # Columnas firma electronica avanzada
    firma_avanzada_nombre: Mapped[Optional[str]] = mapped_column(String(256))
    firma_avanzada_puesto: Mapped[Optional[str]] = mapped_column(String(256))
    firma_avanzada_email: Mapped[Optional[str]] = mapped_column(String(256))
    firma_avanzada_efirma_tiempo: Mapped[Optional[datetime]]
    firma_avanzada_efirma_folio: Mapped[Optional[int]]
    firma_avanzada_efirma_sello_digital: Mapped[Optional[str]] = mapped_column(String(256))
    firma_avanzada_efirma_url: Mapped[Optional[str]] = mapped_column(String(256))
    firma_avanzada_efirma_qr_url: Mapped[Optional[str]] = mapped_column(String(256))
    firma_avanzada_efirma_mensaje: Mapped[Optional[str]] = mapped_column(String(512))
    firma_avanzada_efirma_error: Mapped[Optional[str]] = mapped_column(String(512))
    firma_avanzada_cancelo_tiempo: Mapped[Optional[datetime]]
    firma_avanzada_cancelo_motivo: Mapped[Optional[str]] = mapped_column(String(256))
    firma_avanzada_cancelo_error: Mapped[Optional[str]] = mapped_column(String(512))

    # Hijos
    ofi_documentos_adjuntos: Mapped[List["OfiDocumentosAdjuntos"]] = relationship(back_populates="ofi_documento")
    ofi_documentos_destinatarios: Mapped[List["OfiDocumentosDestinatarios"]] = relationship(back_populates="ofi_documento")

    def __repr__(self):
        """ Representación """
        return f'<OfiDocumento {self.id}>'
