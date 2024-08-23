"""
REPSVM Delitos, modelos
"""

from typing import List

from sqlalchemy import String
from sqlalchemy.orm import Mapped, mapped_column, relationship

from hercules.extensions import database
from lib.universal_mixin import UniversalMixin


class REPSVMDelito(database.Model, UniversalMixin):
    """REPSVMDelito"""

    ESTADOS = {
        "PENDIENTE": "Pendiente",
        "CANCELADO": "Cancelado",
    }

    # Nombre de la tabla
    __tablename__ = "repsvm_delitos"

    # Clave primaria
    id: Mapped[int] = mapped_column(primary_key=True)

    # Columnas
    nombre: Mapped[str] = mapped_column(String(256))

    repsvm_agresores_delitos: Mapped[List["REPSVMAgresorDelito"]] = relationship(back_populates="repsvm_delito")

    def __repr__(self):
        """Representación"""
        return f"<REPSVMDelito {self.id}>"
