"""
Identidades Genero, modelos
"""

from datetime import date
from typing import List, Optional

from sqlalchemy import JSON, Boolean, DateTime, Enum, ForeignKey, Integer, String, Text, Uuid
from sqlalchemy.orm import Mapped, mapped_column, relationship
from sqlalchemy.sql.functions import now

from hercules.extensions import database
from lib.universal_mixin import UniversalMixin


class IdentidadGenero(database.Model, UniversalMixin):
    """IdentidadGenero"""

    GENEROS = {
        "MASCULINO": "Masculino",
        "FEMENINO": "Femenino",
        "NO BINARIO": "No Binario",
    }

    # Nombre de la tabla
    __tablename__ = "identidades_generos"

    # Clave primaria
    id: Mapped[int] = mapped_column(primary_key=True)

    # Columnas
    nombre_anterior: Mapped[str] = mapped_column(String(256))
    nombre_actual: Mapped[str] = mapped_column(String(256))
    fecha_nacimiento: Mapped[date]
    lugar_nacimiento: Mapped[str] = mapped_column(String(256))
    genero_anterior: Mapped[str] = mapped_column(Enum(*GENEROS, name="tipo_genero_anterior", native_enum=False), index=True)
    genero_actual: Mapped[str] = mapped_column(Enum(*GENEROS, name="tipo_genero_actual", native_enum=False), index=True)
    nombre_padre: Mapped[str] = mapped_column(String(256))
    nombre_madre: Mapped[str] = mapped_column(String(256))
    procedimiento: Mapped[str] = mapped_column(String(256))

    def __repr__(self):
        """Representación"""
        return f"<IdentidadGenero {self.id}>"
