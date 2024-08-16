"""
Inventarios Redes, modelos
"""

from datetime import datetime
from typing import List, Optional

from sqlalchemy import JSON, Boolean, DateTime, Enum, ForeignKey, Integer, String, Text, Uuid
from sqlalchemy.orm import Mapped, mapped_column, relationship
from sqlalchemy.sql.functions import now

from hercules.extensions import database
from lib.universal_mixin import UniversalMixin


class InvRed(database.Model, UniversalMixin):
    """InvRed"""

    TIPOS = {
        "LAN": "Lan",
        "WIRELESS": "Wireless",
    }

    # Nombre de la tabla
    __tablename__ = "inv_redes"

    # Clave primaria
    id: Mapped[int] = mapped_column(primary_key=True)

    # Columnas
    nombre: Mapped[str] = mapped_column(String(256), unique=True)
    tipo: Mapped[str] = mapped_column(Enum(*TIPOS, name="inv_redes_tipos", native_enum=False), index=True)

    # Hijos
    inv_equipos: Mapped[List["InvEquipo"]] = relationship(back_populates="inv_red")

    def __repr__(self):
        """Representación"""
        return f"<InvRed {self.id}>"
