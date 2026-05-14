"""
VASPEC Digitalizaciones, modelos
"""

from typing import Optional

from sqlalchemy import ForeignKey, String
from sqlalchemy.orm import Mapped, mapped_column, relationship

from hercules.extensions import database
from lib.universal_mixin import UniversalMixin


class VspDigitalizacion(database.Model, UniversalMixin):
    """VspDigitalizacion"""

    # Nombre de la tabla
    __tablename__ = "vsp_digitalizaciones"

    # Clave primaria
    id: Mapped[int] = mapped_column(primary_key=True)

    # Clave foránea
    autoridad_id: Mapped[int] = mapped_column(ForeignKey("autoridades.id"))
    autoridad: Mapped["Autoridad"] = relationship(back_populates="sentencias")

    # Columnas
    expediente: Mapped[str] = mapped_column(String(16))
    expediente_anio: Mapped[int]
    expediente_num: Mapped[int]
    descripcion: Mapped[Optional[str]] = mapped_column(String(256))
    observaciones: Mapped[Optional[str]] = mapped_column(String(1024))
    archivo: Mapped[str] = mapped_column(String(256), default="", server_default="")
    url: Mapped[str] = mapped_column(String(512), default="", server_default="")

    def __repr__(self):
        """Representación"""
        return f"<VspDigitalizacion {self.id}>"
