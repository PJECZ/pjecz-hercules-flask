"""
Centros de Trabajo, modelos
"""

from datetime import datetime
from typing import List, Optional

from sqlalchemy import JSON, Boolean, DateTime, Enum, ForeignKey, Integer, String, Text, Uuid
from sqlalchemy.orm import Mapped, mapped_column, relationship
from sqlalchemy.sql.functions import now

from hercules.extensions import database
from lib.universal_mixin import UniversalMixin


class CentroTrabajo(database.Model, UniversalMixin):
    """CentroTrabajo"""

    ESTADOS = {
        "PENDIENTE": "Pendiente",
        "CANCELADO": "Cancelado",
    }

    # Nombre de la tabla
    __tablename__ = "centros_trabajos"

    # Clave primaria
    id: Mapped[int] = mapped_column(primary_key=True)

    # Claves foráneas
    distrito_id: Mapped[int] = mapped_column(ForeignKey("distritos.id"))
    distrito: Mapped["Distrito"] = relationship(back_populates="centros_trabajos")
    domicilio_id: Mapped[int] = mapped_column(ForeignKey("domicilios.id"))
    domicilio: Mapped["Domicilio"] = relationship(back_populates="centros_trabajos")

    # Columnas
    clave: Mapped[str] = mapped_column(String(16), unique=True)
    nombre: Mapped[str] = mapped_column(String(256))
    telefono: Mapped[str] = mapped_column(String(48))

    # Hijos
    funcionarios: Mapped[List["Funcionario"]] = relationship("Funcionario", back_populates="centro_trabajo")

    def __repr__(self):
        """Representación"""
        return f"<CentroTrabajo {self.clave}>"
