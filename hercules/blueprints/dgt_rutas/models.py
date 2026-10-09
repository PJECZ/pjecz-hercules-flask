"""
DGT Rutas modelos
"""

import uuid

from sqlalchemy import ForeignKey, String
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from hercules.extensions import database
from lib.universal_mixin import UniversalMixin


class DgtRuta(database.Model, UniversalMixin):
    """DgtRuta"""

    # Nombre de la tabla
    __tablename__ = "dgt_rutas"

    # Clave primaria
    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)

    # Claves foráneas
    dgt_deposito_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("dgt_depositos.id"))
    dgt_deposito: Mapped["DgtDepositos"] = relationship(back_populates="dgt_rutas")
    dgt_tipo_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("dgt_tipos.id"))
    dgt_tipo: Mapped["DgtTipo"] = relationship(back_populates="dgt_rutas")

    # Columnas
    clave: Mapped[str] = mapped_column(String(64), unique=True)
    autoridad_clave: Mapped[str] = mapped_column(String(16))
    directorio: Mapped[str] = mapped_column(String(512))

    # Hijos
    dgt_digitalizaciones: Mapped[list["DgtDigitalizacion"]] = relationship(back_populates="dgt_ruta")
    dgt_entregas: Mapped[list["DgtEntrega"]] = relationship(back_populates="dgt_ruta")

    def __repr__(self):
        """Representación"""
        return f"<DgtRuta {self.id}>"
