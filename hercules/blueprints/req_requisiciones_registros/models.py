"""
Req Requisiciones Registros, modelos
"""

import uuid


from sqlalchemy import ForeignKey, Integer, String, Uuid
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from lib.universal_mixin import UniversalMixin
from hercules.extensions import database
from hercules.blueprints.req_catalogos.models import ReqCatalogo
from hercules.blueprints.req_requisiciones.models import ReqRequisicion


class ReqRequisicionRegistro(database.Model, UniversalMixin):
    """ReqRequisicionRegistro"""

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
    cantidad: Mapped[int] = mapped_column(Integer, nullable=False)
    detalle: Mapped[str] = mapped_column(String(256))
    clave: Mapped[str] = mapped_column(String(30))

    def __repr__(self):
        """Representación"""
        return f"<ReqRequisicionRegistro {self.id}>"
