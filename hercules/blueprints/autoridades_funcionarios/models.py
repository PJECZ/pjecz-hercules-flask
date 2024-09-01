"""
Autoridades Funcionarios, modelos
"""

from datetime import datetime
from typing import List, Optional

from sqlalchemy import JSON, Boolean, DateTime, Enum, ForeignKey, Integer, String, Text, Uuid
from sqlalchemy.orm import Mapped, mapped_column, relationship
from sqlalchemy.sql.functions import now

from hercules.extensions import database
from lib.universal_mixin import UniversalMixin


class AutoridadFuncionario(database.Model, UniversalMixin):
    """AutoridadFuncionario"""

    ESTADOS = {
        "PENDIENTE": "Pendiente",
        "CANCELADO": "Cancelado",
    }

    # Nombre de la tabla
    __tablename__ = "autoridades_funcionarios"

    # Clave primaria
    id: Mapped[int] = mapped_column(primary_key=True)

    # Clave foránea
    autoridad_id: Mapped[int] = mapped_column(ForeignKey("autoridades.id"))
    autoridad: Mapped["Autoridad"] = relationship(back_populates="autoridades_funcionarios")
    funcionario_id: Mapped[int] = mapped_column(ForeignKey("funcionarios.id"))
    funcionario: Mapped["Funcionario"] = relationship(back_populates="autoridades_funcionarios")

    # Columnas
    descripcion: Mapped[str] = mapped_column(String(256))

    def __repr__(self):
        """Representación"""
        return f"<AutoridadFuncionario {self.descripcion}>"
