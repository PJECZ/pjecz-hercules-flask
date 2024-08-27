"""
Inventarios Equipos Fotos, modelos
"""

from sqlalchemy import ForeignKey, String
from sqlalchemy.orm import Mapped, mapped_column, relationship

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
    archivo: Mapped[str] = mapped_column(String(256), default="")
    url: Mapped[str] = mapped_column(String(512), default="")

    def __repr__(self):
        """Representación"""
        return f"<InvEquipoFoto {self.id}>"
