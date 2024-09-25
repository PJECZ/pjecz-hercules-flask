"""
Soportes Adjuntos Tickets, modelos
"""

from datetime import datetime
from typing import List, Optional

from sqlalchemy import Boolean, DateTime, Enum, ForeignKey, JSON, Integer, String, Text, Uuid
from sqlalchemy.orm import Mapped, mapped_column, relationship
from sqlalchemy.sql.functions import now

from lib.universal_mixin import UniversalMixin
from hercules.extensions import database


class SoporteAdjunto(database.Model, UniversalMixin):
    """SoporteAdjunto"""

    # Nombre de la tabla
    __tablename__ = "soportes_adjuntos"

    # Clave primaria
    id: Mapped[int] = mapped_column(primary_key=True)

    # Clave foránea
    soporte_ticket_id: Mapped[int] = mapped_column(ForeignKey("soportes_tickets.id"))
    soporte_ticket: Mapped["SoporteTicket"] = relationship(back_populates="soportes_adjuntos")

    # Columnas
    descripcion: Mapped[str] = mapped_column(String(256))
    archivo: Mapped[str] = mapped_column(String(256))
    url: Mapped[str] = mapped_column(String(512))

    def __repr__(self):
        """Representación"""
        return f"<SoporteAdjunto {self.id}>"
