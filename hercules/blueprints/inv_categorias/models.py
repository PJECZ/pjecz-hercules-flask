"""
Inventarios Categorias, modelos
"""

from datetime import datetime
from typing import List, Optional

from sqlalchemy import JSON, Boolean, DateTime, Enum, ForeignKey, Integer, String, Text, Uuid
from sqlalchemy.orm import Mapped, mapped_column, relationship
from sqlalchemy.sql.functions import now

from hercules.extensions import database
from lib.universal_mixin import UniversalMixin


class InvCategorias(database.Model, UniversalMixin):
    """InvCategorias"""

    # Nombre de la tabla
    __tablename__ = "inv_categorias"

    # Clave primaria
    id: Mapped[int] = mapped_column(primary_key=True)

    # Columnas
    nombre: Mapped[str] = mapped_column(String(256), unique=True)

    # Hijos
    inv_componentes: Mapped[List["InvComponente"]] = relationship(back_populates="inv_categoria")

    def __repr__(self):
        """Representación"""
        return f"<InvCategorias {self.id}>"
