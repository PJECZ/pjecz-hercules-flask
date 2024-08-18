"""
Inventarios Custodias, modelos
"""

from datetime import date
from typing import List

from sqlalchemy import DateTime, ForeignKey, String
from sqlalchemy.orm import Mapped, mapped_column, relationship

from hercules.extensions import database
from lib.universal_mixin import UniversalMixin


class InvCustodia(database.Model, UniversalMixin):
    """InvCustodia"""

    # Nombre de la tabla
    __tablename__ = "inv_custodias"

    # Clave primaria
    id: Mapped[int] = mapped_column(primary_key=True)

    # Clave foránea
    usuario_id: Mapped[int] = mapped_column(ForeignKey("usuarios.id"))
    usuario: Mapped["Usuario"] = relationship(back_populates="inv_custodias")

    # Columnas
    fecha: Mapped[date] = mapped_column(DateTime, index=True)
    curp: Mapped[str] = mapped_column(String(256))
    nombre_completo: Mapped[str] = mapped_column(String(256))
    equipos_cantidad: Mapped[int]
    equipos_fotos_cantidad: Mapped[int]

    # Hijos
    inv_equipos: Mapped[List["InvEquipo"]] = relationship(back_populates="inv_custodia")

    def __repr__(self):
        """Representación"""
        return f"<InvCustodia {self.id}>"
