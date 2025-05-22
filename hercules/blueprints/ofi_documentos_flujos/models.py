"""
Ofi Documentos Flujos, modelos
"""

from datetime import datetime
from typing import List, Optional

from sqlalchemy import Boolean, DateTime, Enum, ForeignKey, JSON, Integer, String, Text, Uuid
from sqlalchemy.orm import Mapped, mapped_column, relationship
from sqlalchemy.sql.functions import now

from lib.universal_mixin import UniversalMixin
from hercules.extensions import database


class OfiDocumentoFlujo(database.Model, UniversalMixin):
    """ OfiDocumentoFlujo """

    ESTADOS = {
        "PENDIENTE": "Pendiente",
        "COMPLETADO": "Completado",
        "CANCELADO": "Cancelado",
    }

    # Nombre de la tabla
    __tablename__ = 'ofi_documentos_flujos'

    # Clave primaria
    id: Mapped[int] = mapped_column(primary_key=True)

    # Clave foránea
    ofi_documento_id: Mapped[int] = mapped_column(ForeignKey("ofi_documentos.id"))
    ofi_documento: Mapped["OfiDocumento"] = relationship(back_populates="ofi_documentos_flujos")
    usuario_id: Mapped[int] = mapped_column(ForeignKey("usuarios.id"))
    usuario: Mapped["Usuario"] = relationship(back_populates="ofi_documentos_flujos")

    # Columnas
    orden: Mapped[int]
    descripcion: Mapped[str] = mapped_column(String(256))
    estado: Mapped[str] = mapped_column(Enum(*ESTADOS, name="ofi_documentos_flujos_estados", native_enum=False), index=True)

    def __repr__(self):
        """ Representación """
        return f'<OfiDocumentoFlujo {self.id}>'
