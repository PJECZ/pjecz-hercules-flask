"""
Materias, modelos
"""

from typing import List

from sqlalchemy import Boolean, Column, Integer, String
from sqlalchemy.orm import Mapped, mapped_column, relationship

from hercules.extensions import database
from lib.universal_mixin import UniversalMixin


class Materia(database.Model, UniversalMixin):
    """Materia"""

    # Nombre de la tabla
    __tablename__ = "materias"

    # Clave primaria
    id: Mapped[int] = mapped_column(primary_key=True)

    # Columnas
    nombre: Mapped[str] = mapped_column(String(256), unique=True)
    descripcion: Mapped[str] = mapped_column(String(1024))
    en_sentencias: Mapped[bool] = mapped_column(Boolean, default=False)

    # Hijos
    autoridades: Mapped[List["Autoridad"]] = relationship("Autoridad", back_populates="materia")

    def __repr__(self):
        """Representación"""
        return f"<Materia {self.nombre}>"
