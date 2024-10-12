"""
CID Formatos, modelos
"""

from sqlalchemy import ForeignKey, String
from sqlalchemy.orm import Mapped, mapped_column, relationship

from hercules.extensions import database
from lib.universal_mixin import UniversalMixin


class CIDFormato(database.Model, UniversalMixin):
    """CIDFormato"""

    # Nombre de la tabla
    __tablename__ = "cid_formatos"

    # Clave primaria
    id: Mapped[int] = mapped_column(primary_key=True)

    # Clave foránea
    procedimiento_id: Mapped[int] = mapped_column(ForeignKey("cid_procedimientos.id"))
    procedimiento: Mapped["CIDProcedimiento"] = relationship(back_populates="cid_formatos")
    cid_area_id: Mapped[int] = mapped_column(ForeignKey("cid_areas.id"))
    cid_area: Mapped["CIDArea"] = relationship(back_populates="cid_formatos")

    # Columnas
    codigo: Mapped[str] = mapped_column(String(16), default="")
    descripcion: Mapped[str] = mapped_column(String(256))
    archivo: Mapped[str] = mapped_column(String(256), default="", server_default="")
    url: Mapped[str] = mapped_column(String(512), default="", server_default="")

    def __repr__(self):
        """Representación"""
        return f"<CIDFormato {self.id}>"
