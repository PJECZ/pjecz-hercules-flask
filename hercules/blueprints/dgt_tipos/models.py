"""
DGT Tipos modelos
"""

import uuid

from sqlalchemy import String
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from hercules.extensions import database
from lib.universal_mixin import UniversalMixin


class DgtTipo(database.Model, UniversalMixin):
    """DgtTipo"""

    # Nombre de la tabla
    __tablename__ = "dgt_tipos"

    # Clave primaria
    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)

    # Columnas
    clave: Mapped[str] = mapped_column(String(64), unique=True)
    descripcion: Mapped[str] = mapped_column(String(256))

    # Hijos
    dgt_rutas: Mapped[list["DgtRuta"]] = relationship(back_populates="dgt_tipo")

    def __repr__(self):
        """Representación"""
        return f"<DgtTipo {self.id}>"
