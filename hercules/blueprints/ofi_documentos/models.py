"""
Ofi Documentos, modelos
"""

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
        "CANCELADO": "Cancelado",
    }

    # Nombre de la tabla
    __tablename__ = 'ofi_documentos'

    # Clave primaria
    id: Mapped[int] = mapped_column(primary_key=True)

    # Clave foránea
    ofi_plantilla_id: Mapped[int] = mapped_column(ForeignKey("ofi_plantillas.id"))
    ofi_plantilla: Mapped["OfiPlantilla"] = relationship(back_populates="ofi_documentos")
    usuario_id: Mapped[int] = mapped_column(ForeignKey("usuarios.id"))
    usuario: Mapped["Usuario"] = relationship(back_populates="ofi_documentos")

    # Columnas
    titulo: Mapped[str] = mapped_column(String(256))
    folio: Mapped[Optional[int]]
    contenido: Mapped[str] = mapped_column(Text)
    estado: Mapped[str] = mapped_column(Enum(*ESTADOS, name="ofi_documentos_estados", native_enum=False), index=True)

    # Hijos
    ofi_documentos_comentarios: Mapped[List["OfiDocumentosComentario"]] = relationship(back_populates="ofi_documento")
    ofi_documentos_firmas: Mapped[List["OfiDocumentosFirma"]] = relationship(back_populates="ofi_documento")
    ofi_documentos_flujos: Mapped[List["OfiDocumentosFlujo"]] = relationship(back_populates="ofi_documento")

    def __repr__(self):
        """ Representación """
        return f'<OfiDocumento {self.id}>'
