"""
Archivo - Documentos Bitacoras, modelos
"""

from datetime import datetime
from typing import List, Optional

from sqlalchemy import Boolean, DateTime, Enum, ForeignKey, JSON, Integer, String, Text, Uuid
from sqlalchemy.orm import Mapped, mapped_column, relationship
from sqlalchemy.sql.functions import now

from lib.universal_mixin import UniversalMixin
from hercules.extensions import database


class ArcDocumentoBitacora(database.Model, UniversalMixin):
    """ArcDocumentoBitacora"""

    ACCIONES = {
        "ALTA": "Alta",
        "EDICION DOC": "Edición del Documento",
        "CORRECCION FOJAS": "Corrección de Fojas",
        "NO ENCONTRADO": "No Encontrado",
        "ENVIADO": "Enviado",
        "ENTREGADO": "Entregado",
        "ARCHIVAR": "Archivar",
        "ANOMALIA": "Anomalía",
        "ELIMINADO": "Eliminado",
        "RECUPERADO": "Recuperado",
    }

    # Nombre de la tabla
    __tablename__ = "arc_documentos_bitacoras"

    # Clave primaria
    id: Mapped[int] = mapped_column(primary_key=True)

    # Clave foránea
    arc_documento_id: Mapped[int] = mapped_column(ForeignKey("arc_documentos.id"))
    arc_documento: Mapped["ArcDocumento"] = relationship(back_populates="arc_documentos_bitacoras")
    usuario_id: Mapped[int] = mapped_column(ForeignKey("usuarios.id"))
    usuario: Mapped["Usuario"] = relationship(back_populates="arc_documentos_bitacoras")

    # Columnas
    fojas: Mapped[int]
    accion: Mapped[str] = mapped_column(
        Enum(*ACCIONES, name="arc_documentos_bitacoras_acciones", native_enum=False), index=True
    )
    observaciones: Mapped[str] = mapped_column(String(256))

    def __repr__(self):
        """Representación"""
        return f"<ArcDocumentoBitacora {self.id}>"
