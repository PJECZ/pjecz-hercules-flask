"""
Web Unidades, modelos
"""

from sqlalchemy import Column, Integer, String
from sqlalchemy.orm import relationship

from lib.universal_mixin import UniversalMixin

from hercules.extensions import database


class WebUnidad(database.Model, UniversalMixin):
    """WebUnidad"""

    # Nombre de la tabla
    __tablename__ = "web_unidades"

    # Clave primaria
    id = Column(Integer, primary_key=True)

    # Columnas
    clave = Column(String(16), unique=True, nullable=False)
    nombre = Column(String(256), nullable=False)

    # Hijos
    # web_paginas = relationship("WebPagina", back_populates="web_unidad")

    def __repr__(self):
        """Representación"""
        return f"<WebUnidad {self.clave}>"
