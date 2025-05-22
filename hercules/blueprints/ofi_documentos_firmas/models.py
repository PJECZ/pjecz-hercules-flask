"""
Ofi Documentos Firmas, modelos
"""

from sqlalchemy import Enum, ForeignKey
from sqlalchemy.orm import Mapped, mapped_column, relationship

from lib.universal_mixin import UniversalMixin
from hercules.extensions import database


class OfiDocumentoFirma(database.Model, UniversalMixin):
    """ OfiDocumentoFirma """

    ESTADOS = {
        "PENDIENTE": "Pendiente",
        "FIRMADO": "Firmado",
        "CANCELADO": "Cancelado",
    }

    # Nombre de la tabla
    __tablename__ = 'ofi_documentos_firmas'

    # Clave primaria
    id: Mapped[int] = mapped_column(primary_key=True)

    # Clave foránea
    ofi_documento_id: Mapped[int] = mapped_column(ForeignKey("ofi_documentos.id"))
    ofi_documento: Mapped["OfiDocumento"] = relationship(back_populates="ofi_documentos_firmas")

    # Columnas
    estado: Mapped[str] = mapped_column(Enum(*ESTADOS, name="ofi_documentos_firmas_estados", native_enum=False), index=True)

    def __repr__(self):
        """ Representación """
        return f'<OfiDocumentoFirma {self.id}>'
