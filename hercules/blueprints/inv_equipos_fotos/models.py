"""
Inventarios Equipos Fotos, modelos
"""

from datetime import datetime
from typing import List, Optional

from sqlalchemy import JSON, Boolean, DateTime, Enum, ForeignKey, Integer, String, Text, Uuid
from sqlalchemy.orm import Mapped, mapped_column, relationship
from sqlalchemy.sql.functions import now

from hercules.extensions import database
from lib.universal_mixin import UniversalMixin


class InvEquipoFoto(database.Model, UniversalMixin):
    """InvEquipoFoto"""

    # Nombre de la tabla
    __tablename__ = "inv_equipos_fotos"

    # Clave primaria
    id: Mapped[int] = mapped_column(primary_key=True)

    # Clave foránea
    inv_equipo_id: Mapped[int] = mapped_column(ForeignKey("inv_equipos.id"))
    inv_equipo: Mapped["InvEquipo"] = relationship(back_populates="inv_equipos_fotos")

    # Columnas
    descripcion: Mapped[str] = mapped_column(String(256))
    archivo: Mapped[str] = mapped_column(String(256))
    url: Mapped[str] = mapped_column(String(512))

    def __repr__(self):
        """Representación"""
        return f"<InvEquipoFoto {self.id}>"
