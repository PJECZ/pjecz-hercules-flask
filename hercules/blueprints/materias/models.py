"""
Materias, modelos
"""

from sqlalchemy import Boolean, Column, Integer, String
from sqlalchemy.orm import relationship

from lib.universal_mixin import UniversalMixin
from hercules.extensions import database


class Materia(database.Model, UniversalMixin):
    """Materia"""

    # Nombre de la tabla
    __tablename__ = "materias"

    # Clave primaria
    id = Column(Integer, primary_key=True)

    # Columnas
    nombre = Column(String(64), nullable=False, unique=True)
    descripcion = Column(String(1024), nullable=True)
    en_sentencias = Column(Boolean, nullable=False, default=False)

    # Hijos
    autoridades = relationship("Autoridad", back_populates="materia")

    def __repr__(self):
        """Representación"""
        return f"<Materia {self.nombre}>"
