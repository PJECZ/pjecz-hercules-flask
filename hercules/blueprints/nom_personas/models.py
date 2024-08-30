"""
Nominas Personas, modelos
"""

from typing import Optional

from sqlalchemy import String
from sqlalchemy.orm import Mapped, mapped_column

from lib.universal_mixin import UniversalMixin
from hercules.extensions import database


class NomPersona(database.Model, UniversalMixin):
    """NomPersona"""

    # Nombre de la tabla
    __tablename__ = "nom_personas"

    # Clave primaria
    id: Mapped[int] = mapped_column(primary_key=True)

    # Columnas
    rfc: Mapped[str] = mapped_column(String(13), unique=True)
    nombres: Mapped[str] = mapped_column(String(128))
    apellido_primero: Mapped[str] = mapped_column(String(128))
    apellido_segundo: Mapped[Optional[str]] = mapped_column(String(128))

    def __repr__(self):
        """Representación"""
        return f"<NomPersona {self.id}>"
