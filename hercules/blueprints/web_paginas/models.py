"""
Web Paginas, modelos
"""

from sqlalchemy import Column, Date, ForeignKey, JSON, Integer, String
from sqlalchemy.orm import relationship

from lib.universal_mixin import UniversalMixin

from hercules.extensions import database


class WebPagina(database.Model, UniversalMixin):
    """WebPagina"""

    # Nombre de la tabla
    __tablename__ = "web_paginas"

    # Clave primaria
    id = Column(Integer, primary_key=True)

    # Clave foránea
    web_unidad_id = Column(Integer, ForeignKey("web_unidades.id"), index=True, nullable=False)
    web_unidad = relationship("WebUnidad", back_populates="web_paginas")

    # Columnas
    titulo = Column(String(256), nullable=False)
    fecha_modificacion = Column(Date, nullable=False)
    responsable = Column(String(256), nullable=False)
    ruta = Column(String(256), nullable=False)
    contenido = Column(JSON, nullable=False)

    # Hijos
    web_archivos = relationship("WebArchivo", back_populates="web_pagina")

    def __repr__(self):
        """Representación"""
        return f"<WebPagina {self.id}>"
