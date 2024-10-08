"""
Archivo - Remesas Bitácoras, modelos
"""

from datetime import datetime
from typing import List, Optional

from sqlalchemy import Boolean, DateTime, Enum, ForeignKey, JSON, Integer, String, Text, Uuid
from sqlalchemy.orm import Mapped, mapped_column, relationship
from sqlalchemy.sql.functions import now

from lib.universal_mixin import UniversalMixin
from hercules.extensions import database


class ArcRemesaBitacora(database.Model, UniversalMixin):
    """ArcRemesaBitacora"""

    ACCIONES = {
        "CREADA": "Creada",
        "MODIFICADA": "Modificada",
        "CANCELADA": "Cancelada",
        "ENVIADA": "Enviada",
        "ASIGNADA": "Asignar",
        "RECHAZADA": "Rechazada",
        "ARCHIVADA": "Archivada",
        "ARCHIVADA CON ANOMALIA": "Archivado con Anomalía",  # El ARCHIVISTA termina de procesar la remesa pero almenos un documento presentó anomalía
        "ANOMALIA GENERAL": "Anomalía General",
        "PASADA AL HISTORIAL": "Pasada al Historial",
    }

    # Nombre de la tabla
    __tablename__ = "arc_remesas_bitacoras"

    # Clave primaria
    id: Mapped[int] = mapped_column(primary_key=True)

    # Clave foránea
    arc_remesa_id: Mapped[int] = mapped_column(ForeignKey("arc_remesas.id"))
    arc_remesa: Mapped["ArcRemesa"] = relationship(back_populates="arc_remesas_bitacoras")
    usuario_id: Mapped[int] = mapped_column(ForeignKey("usuarios.id"))
    usuario: Mapped["Usuario"] = relationship(back_populates="arc_remesas_bitacoras")

    # Columnas
    accion: Mapped[str] = mapped_column(Enum(*ACCIONES, name="arc_remesas_bitacoras_acciones", native_enum=False), index=True)
    observaciones: Mapped[str] = mapped_column(String(256))

    def __repr__(self):
        """Representación"""
        return f"<ArcRemesaBitacora {self.id}>"
