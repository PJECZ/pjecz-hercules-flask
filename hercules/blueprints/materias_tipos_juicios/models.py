"""
Materias-Tipos de Juicios, modelos
"""

from datetime import datetime
from typing import List, Optional

from sqlalchemy import JSON, Boolean, DateTime, Enum, ForeignKey, Integer, String, Text, Uuid
from sqlalchemy.orm import Mapped, mapped_column, relationship
from sqlalchemy.sql.functions import now

from hercules.extensions import database
from lib.universal_mixin import UniversalMixin


class MateriaTipoJuicio(database.Model, UniversalMixin):
    """MateriaTipoJuicio"""

    ESTADOS = {
        "PENDIENTE": "Pendiente",
        "CANCELADO": "Cancelado",
    }

    # Nombre de la tabla
    __tablename__ = "materias_tipos_juicios"

    # Clave primaria
    id: Mapped[int] = mapped_column(primary_key=True)

    # Clave foránea
    materia_id: Mapped[int] = mapped_column(ForeignKey("materias.id"))
    materia: Mapped["Materia"] = relationship(back_populates="materias_tipos_juicios")

    # Columnas
    descripcion: Mapped[str] = mapped_column(String(256))

    # Hijos
    sentencias: Mapped[List["Sentencia"]] = relationship("Sentencia", back_populates="materia_tipo_juicio")

    def __repr__(self):
        """Representación"""
        return f"<MateriaTipoJuicio {self.id}>"
