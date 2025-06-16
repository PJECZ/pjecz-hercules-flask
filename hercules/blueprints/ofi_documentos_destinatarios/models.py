"""
Ofi Documentos Destinatarios, modelos
"""

from datetime import datetime
from typing import Optional

from sqlalchemy import ForeignKey
from sqlalchemy.orm import Mapped, mapped_column, relationship

from lib.universal_mixin import UniversalMixin
from hercules.extensions import database


class OfiDocumentoDestinatario(database.Model, UniversalMixin):
    """OfiDocumentoDestinatario"""

    # Nombre de la tabla
    __tablename__ = "ofi_documentos_destinatarios"

    # Clave primaria
    id: Mapped[int] = mapped_column(primary_key=True)

    # Clave foránea
    ofi_documento_id: Mapped[int] = mapped_column(ForeignKey("ofi_documentos.id"))
    ofi_documento: Mapped["OfiDocumento"] = relationship(back_populates="ofi_documentos_destinatarios")
    usuario_id: Mapped[int] = mapped_column(ForeignKey("usuarios.id"))
    usuario: Mapped["Usuario"] = relationship(back_populates="ofi_documentos_destinatarios")

    # Columnas
    con_copia: Mapped[bool] = mapped_column(default=False)
    fue_leido: Mapped[bool] = mapped_column(default=False)
    fue_leido_tiempo: Mapped[Optional[datetime]]

    def __repr__(self):
        """Representación"""
        return f"<OfiDocumentoDestinatario {self.id}>"
