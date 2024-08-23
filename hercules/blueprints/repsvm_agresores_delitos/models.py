"""
REPSVM Agresores-Delitos, modelos
"""

from sqlalchemy import ForeignKey
from sqlalchemy.orm import Mapped, mapped_column, relationship

from hercules.extensions import database
from lib.universal_mixin import UniversalMixin


class REPSVMAgresorDelito(database.Model, UniversalMixin):
    """REPSVMAgresorDelito"""

    # Nombre de la tabla
    __tablename__ = "respsvm_agresores_delitos"

    # Clave primaria
    id: Mapped[int] = mapped_column(primary_key=True)

    # Clave foránea
    repsvm_agresor_id: Mapped[int] = mapped_column(ForeignKey("repsvm_agresores.id"))
    repsvm_agresor: Mapped["REPSVMAgresor"] = relationship(back_populates="repsvm_agresores_delitos")
    repsvm_delito_id: Mapped[int] = mapped_column(ForeignKey("repsvm_delitos.id"))
    repsvm_delito: Mapped["REPSVMDelito"] = relationship(back_populates="repsvm_agresores_delitos")

    def __repr__(self):
        """Representación"""
        return f"<REPSVMAgresorDelito {self.id}>"
