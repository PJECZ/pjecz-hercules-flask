"""
Inventarios Marcas, modelos
"""

from typing import List

from sqlalchemy import String
from sqlalchemy.orm import Mapped, mapped_column, relationship

from hercules.extensions import database
from lib.universal_mixin import UniversalMixin


class InvMarca(database.Model, UniversalMixin):
    """InvMarca"""

    # Nombre de la tabla
    __tablename__ = "inv_marcas"

    # Clave primaria
    id: Mapped[int] = mapped_column(primary_key=True)

    # Columnas
    nombre: Mapped[str] = mapped_column(String(256), unique=True, nullable=False)

    # Hijos
    inv_modelos: Mapped[List["InvModelo"]] = relationship("InvModelo", back_populates="inv_marca")

    def __repr__(self):
        """Representación"""
        return f"<InvMarca {self.id}>"
