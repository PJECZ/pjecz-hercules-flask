"""
Ofi Documentos Comentarios, modelos
"""

from sqlalchemy import Enum, ForeignKey, Text
from sqlalchemy.orm import Mapped, mapped_column, relationship

from lib.universal_mixin import UniversalMixin
from hercules.extensions import database


class OfiDocumentoComentario(database.Model, UniversalMixin):
    """ OfiDocumentoComentario """

    ESTADOS = {
        "PENDIENTE": "Pendiente",
        "ACEPTADO": "Aceptado",
        "CANCELADO": "Cancelado",
        "RECHAZADO": "Rechazado",
    }

    # Nombre de la tabla
    __tablename__ = 'ofi_comentarios'

    # Clave primaria
    id: Mapped[int] = mapped_column(primary_key=True)

    # Clave foránea
    ofi_documento_id: Mapped[int] = mapped_column(ForeignKey("ofi_documentos.id"))
    ofi_documento: Mapped["OfiDocumento"] = relationship(back_populates="ofi_documentos_comentarios")
    usuario_id: Mapped[int] = mapped_column(ForeignKey("usuarios.id"))
    usuario: Mapped["Usuario"] = relationship(back_populates="ofi_documentos")

    # Columnas
    comentario: Mapped[str] = mapped_column(Text)
    estado: Mapped[str] = mapped_column(Enum(*ESTADOS, name="ofi_comentarios_estados", native_enum=False), index=True)

    def __repr__(self):
        """ Representación """
        return f'<OfiComentario {self.id}>'
