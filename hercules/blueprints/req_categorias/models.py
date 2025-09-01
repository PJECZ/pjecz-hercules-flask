"""
Requisiciones Categorías, modelos
"""

from typing import List

from sqlalchemy import String
from sqlalchemy.orm import Mapped, mapped_column, relationship

from lib.universal_mixin import UniversalMixin
from hercules.extensions import database


class ReqCategoria(database.Model, UniversalMixin):
    """ReqCategoria"""

    # Nombre de la tabla
    __tablename__ = "req_categorias"

    # Clave primaria
    id: Mapped[int] = mapped_column(primary_key=True)

    # Columnas
    clave: Mapped[str] = mapped_column(String(16), unique=True)
    descripcion: Mapped[str] = mapped_column(String(256))

    # Hijos
    req_catalogos: Mapped[List["ReqCatalogo"]] = relationship(back_populates="req_categoria")

    @property
    def clave_descripcion(self):
        """Junta clave y descripcion"""
        return self.clave + ": " + self.descripcion

    def __repr__(self):
        """Representación"""
        return f"<ReqCategoria {self.id}>"
