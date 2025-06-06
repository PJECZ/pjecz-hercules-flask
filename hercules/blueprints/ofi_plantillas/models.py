"""
Ofi Plantillas, modelos
"""

from typing import Optional

from sqlalchemy import ForeignKey, String, Text
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import Mapped, mapped_column, relationship

from lib.universal_mixin import UniversalMixin
from hercules.extensions import database


class OfiPlantilla(database.Model, UniversalMixin):
    """OfiPlantilla"""

    # Nombre de la tabla
    __tablename__ = "ofi_plantillas"

    # Clave primaria
    id: Mapped[int] = mapped_column(primary_key=True)

    # Clave foránea
    usuario_id: Mapped[int] = mapped_column(ForeignKey("usuarios.id"))
    usuario: Mapped["Usuario"] = relationship(back_populates="ofi_plantillas")

    # Columnas
    descripcion: Mapped[str] = mapped_column(String(256))
    contenido: Mapped[str] = mapped_column(Text)
    variables: Mapped[Optional[JSONB]] = mapped_column(JSONB)
    es_activo: Mapped[bool] = mapped_column(default=True)

    def __repr__(self):
        """Representación"""
        return f"<OfiPlantilla {self.id}>"
