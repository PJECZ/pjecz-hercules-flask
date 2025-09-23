"""
Req Requisiciones Registros, modelos
"""

import uuid

from sqlalchemy import ForeignKey, Integer, String, Enum
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from lib.universal_mixin import UniversalMixin
from hercules.extensions import database


class ReqRequisicionRegistro(database.Model, UniversalMixin):
    """ReqRequisicionRegistro"""

    CLAVES = {
        "INS": "INSUFICIENCIA",
        "REP": "REPOSICION DE BIENES",
        "OBS": "OBSOLESENCIA",
        "AMP": "AMPLIACION COBERTURA DEL SERVICIO",
        "NUE": "NUEVO PROYECTO",
    }

    # Nombre de la tabla
    __tablename__ = "req_requisiciones_registros"

    # Clave primaria
    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)

    # Clave foránea
    req_catalogo_id: Mapped[int] = mapped_column(ForeignKey("req_catalogos.id"))
    req_catalogo: Mapped["ReqCatalogo"] = relationship(back_populates="req_requisiciones_registros")
    req_requisicion_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("req_requisiciones.id"))
    req_requisicion: Mapped["ReqRequisicion"] = relationship(back_populates="req_requisiciones_registros")

    # Columnas
    clave: Mapped[str] = mapped_column(Enum(*CLAVES, name="req_requisiciones_registros_claves", native_enum=False), index=True)
    # clave: Mapped[str] = mapped_column(String(30))
    cantidad: Mapped[int] = mapped_column(Integer, nullable=False)
    detalle: Mapped[str] = mapped_column(String(256))

    def __repr__(self):
        """Representación"""
        return f"<ReqRequisicionRegistro {self.id}>"
