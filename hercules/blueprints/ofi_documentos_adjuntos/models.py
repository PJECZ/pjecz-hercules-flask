"""
Ofi Documentos Ajuntos, modelos
"""

from sqlalchemy import ForeignKey, String
from sqlalchemy.orm import Mapped, mapped_column, relationship

from lib.universal_mixin import UniversalMixin
from hercules.extensions import database


class OfiDocumentoAdjunto(database.Model, UniversalMixin):
    """ OfiDocumentoAdjunto """

    # Nombre de la tabla
    __tablename__ = 'ofi_documentos_adjuntos'

    # Clave primaria
    id: Mapped[int] = mapped_column(primary_key=True)

    # Clave foránea
    ofi_documento_id: Mapped[int] = mapped_column(ForeignKey("ofi_documentos.id"))
    ofi_documento: Mapped["OfiDocumento"] = relationship(back_populates="ofi_documentos_adjuntos")

    # Columnas
    descripcion: Mapped[str] = mapped_column(String(256))
    archivo: Mapped[str] = mapped_column(String(256), default="")
    url: Mapped[str] = mapped_column(String(512), default="")

    def __repr__(self):
        """ Representación """
        return f'<OfiDocumentoAdjunto {self.id}>'
