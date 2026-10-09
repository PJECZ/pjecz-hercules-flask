"""
DGT Depósitos modelos
"""

import uuid

from sqlalchemy import Enum, String
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from hercules.extensions import database
from lib.universal_mixin import UniversalMixin


class DgtDepositos(database.Model, UniversalMixin):
    """DgtDepositos"""

    PROPOSITOS = {
        "ND": "No Definido",
        "ENTREGAS": "Entregas",
        "DIGITALIZACIONES": "Digitalizaciones",
        "RESPALDOS": "Respaldos",
    }

    # Nombre de la tabla
    __tablename__ = "dgt_depositos"

    # Clave primaria
    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)

    # Columnas
    clave: Mapped[str] = mapped_column(String(64), unique=True)
    descripcion: Mapped[str] = mapped_column(String(256))
    proposito: Mapped[str] = mapped_column(Enum(*PROPOSITOS, name="dgt_depositos_propositos", native_enum=False), index=True)

    # Hijos
    dgt_rutas: Mapped[list["DgtRuta"]] = relationship(back_populates="dgt_deposito")

    def __repr__(self):
        """Representación"""
        return f"<DgtDepositos {self.id}>"
