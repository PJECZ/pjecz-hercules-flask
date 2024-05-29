"""
Web Archivos, modelos
"""

from sqlalchemy import Column, ForeignKey, Integer, String
from sqlalchemy.orm import relationship

from lib.universal_mixin import UniversalMixin

from hercules.extensions import database


class WebArchivo(database.Model, UniversalMixin):
    """WebArchivo"""

    # Nombre de la tabla
    __tablename__ = "web_archivos"

    # Clave primaria
    id = Column(Integer, primary_key=True)

    # Clave foránea
    web_pagina_id = Column(Integer, ForeignKey("web_paginas.id"), index=True, nullable=False)
    web_pagina = relationship("WebPagina", back_populates="web_archivos")

    # Columnas
    archivo = Column(String(256), nullable=False)
    descripcion = Column(String(256), nullable=False)
    url = Column(String(256), nullable=False)

    def __repr__(self):
        """Representación"""
        return f"<WebArchivo {self.id}>"
