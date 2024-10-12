"""
Cid Areas Autoridades, modelos
"""

from datetime import datetime
from typing import List, Optional

from sqlalchemy import JSON, Boolean, DateTime, Enum, ForeignKey, Integer, String, Text, Uuid
from sqlalchemy.orm import Mapped, mapped_column, relationship
from sqlalchemy.sql.functions import now

from hercules.extensions import database
from lib.universal_mixin import UniversalMixin


class CIDAreaAutoridad(database.Model, UniversalMixin):
    """CIDAreaAutoridad"""

    # Nombre de la tabla
    __tablename__ = "cid_areas_autoridades"

    # Clave primaria
    id: Mapped[int] = mapped_column(primary_key=True)

    # Clave foránea
    autoridad_id: Mapped[int] = mapped_column(ForeignKey("autoridades.id"))
    autoridad: Mapped["Autoridad"] = relationship(back_populates="cid_areas_autoridades")
    cid_area_id: Mapped[int] = mapped_column(ForeignKey("cid_areas.id"))
    cid_area: Mapped["CIDArea"] = relationship(back_populates="cid_areas_autoridades")

    # Columnas
    descripcion: Mapped[str] = mapped_column(String(256))

    def __repr__(self):
        """Representación"""
        return f"<CIDAreaAutoridad {self.descripcion}>"
