"""
Archivo - Documentos Tipos, modelos
"""

from datetime import datetime
from typing import List, Optional

from sqlalchemy import Boolean, DateTime, Enum, ForeignKey, JSON, Integer, String, Text, Uuid
from sqlalchemy.orm import Mapped, mapped_column, relationship
from sqlalchemy.sql.functions import now

from lib.universal_mixin import UniversalMixin
from hercules.extensions import database


class ArcDocumentoTipo(database.Model, UniversalMixin):
    """ArcDocumentoTipo"""

    # Nombre de la tabla
    __tablename__ = "arc_documentos_tipos"

    # Clave primaria
    id: Mapped[int] = mapped_column(primary_key=True)

    # Columnas
    nombre: Mapped[str] = mapped_column(String(32), unique=True)

    # Hijos TODO:
    arc_documentos: Mapped[List["ArcDocumento"]] = relationship(back_populates="arc_documento_tipo")
    # arc_remesas = db.relationship("ArcRemesa", back_populates="arc_documento_tipo", lazy="noload")

    def __repr__(self):
        """Representación"""
        return f"<ArcDocumentoTipo {self.id}>"
