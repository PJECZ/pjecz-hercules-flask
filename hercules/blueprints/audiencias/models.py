"""
Audiencias, modelos
"""

from datetime import datetime
from typing import List, Optional

from sqlalchemy import JSON, Boolean, DateTime, Enum, ForeignKey, Integer, String, Text, Uuid
from sqlalchemy.orm import Mapped, mapped_column, relationship
from sqlalchemy.sql.functions import now

from hercules.extensions import database
from lib.universal_mixin import UniversalMixin


class Audiencia(database.Model, UniversalMixin):
    """Audiencia"""

    CARACTERES = {
        "NO DEFINIDO": "No definido",
        "PUBLICA": "Pública",
        "PRIVADA": "Privada",
    }

    # Nombre de la tabla
    __tablename__ = "audiencias"

    # Clave primaria
    id: Mapped[int] = mapped_column(primary_key=True)

    # Clave foránea
    autoridad_id: Mapped[int] = mapped_column(ForeignKey("autoridades.id"))
    autoridad: Mapped["Autoridad"] = relationship(back_populates="audiencias")

    # Columnas comunes
    tiempo: Mapped[datetime]
    tipo_audiencia: Mapped[str] = mapped_column(String(256))

    # Columnas para Materias C F M L D(CyF) Salas (CyF) TCyA
    expediente: Mapped[str] = mapped_column(String(64))
    actores: Mapped[str] = mapped_column(String(256))
    demandados: Mapped[str] = mapped_column(String(256))

    # Columnas para Materia Acusatorio Penal Oral
    sala: Mapped[str] = mapped_column(String(256))
    caracter: Mapped[str] = mapped_column(Enum(*CARACTERES, name="tipos_caracteres", native_enum=False))
    causa_penal: Mapped[str] = mapped_column(String(256))
    delitos: Mapped[str] = mapped_column(String(256))

    # Columnas para Distritales Penales
    toca: Mapped[str] = mapped_column(String(256))
    expediente_origen: Mapped[str] = mapped_column(String(256))
    imputados: Mapped[str] = mapped_column(String(256))

    # Columnas para Salas Penales
    # toca
    # expediente_origen
    # delitos
    origen: Mapped[str] = mapped_column(String(256))

    def __repr__(self):
        """Representación"""
        return f"<Audiencia {self.id}>"
