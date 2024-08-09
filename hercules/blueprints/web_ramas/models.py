"""
Web Ramas, modelos
"""

from typing import List

from sqlalchemy import String
from sqlalchemy.orm import Mapped, mapped_column, relationship

from hercules.extensions import database
from lib.universal_mixin import UniversalMixin


class WebRama(database.Model, UniversalMixin):
    """WebRama"""

    # Nombre de la tabla
    __tablename__ = "web_ramas"

    # Clave primaria
    id: Mapped[int] = mapped_column(primary_key=True)

    # Columnas
    clave: Mapped[str] = mapped_column(String(16), unique=True)
    nombre: Mapped[str] = mapped_column(String(256))

    # Hijos
    web_paginas: Mapped[List["WebPagina"]] = relationship("WebPagina", back_populates="web_rama")

    def __repr__(self):
        """Representación"""
        return f"<WebUnidad {self.clave}>"
