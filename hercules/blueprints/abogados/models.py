"""
Abogados, modelos
"""

from datetime import date

from sqlalchemy import String
from sqlalchemy.orm import Mapped, mapped_column

from hercules.extensions import database
from lib.universal_mixin import UniversalMixin


class Abogado(database.Model, UniversalMixin):
    """Abogado"""

    # Nombre de la tabla
    __tablename__ = "abogados"

    # Clave primaria
    id: Mapped[int] = mapped_column(primary_key=True)

    # Columnas
    fecha: Mapped[date]
    numero: Mapped[str] = mapped_column(String(24))
    libro: Mapped[str] = mapped_column(String(24))
    nombre: Mapped[str] = mapped_column(String(256))

    def __repr__(self):
        """Representación"""
        return f"<Abogado {self.id}>"
