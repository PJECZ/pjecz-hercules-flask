"""
Estados, modelos
"""

from sqlalchemy import Column, Integer, String
from sqlalchemy.orm import relationship

from lib.universal_mixin import UniversalMixin

from hercules.extensions import database


class Estado(database.Model, UniversalMixin):
    """Estado"""

    # Nombre de la tabla
    __tablename__ = "estados"

    # Clave primaria
    id = Column(Integer, primary_key=True)

    # Columnas
    clave = Column(String(2), nullable=False, unique=True)
    nombre = Column(String(256), nullable=False)

    # Hijos
    municipios = relationship("Municipio", back_populates="estado")

    def __repr__(self):
        """Representación"""
        return f"<Estado {self.clave}>"
