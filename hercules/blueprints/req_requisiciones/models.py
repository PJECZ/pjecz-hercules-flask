"""
Req Requisiciones, modelos
"""

from datetime import datetime, date
import uuid
from typing import List, Optional

from sqlalchemy import Boolean, Date, DateTime, Enum, ForeignKey, JSON, Integer, String, Text, Uuid
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship
from sqlalchemy.sql.functions import now

from lib.universal_mixin import UniversalMixin
from hercules.extensions import database


class ReqRequisicion(database.Model, UniversalMixin):
    """ReqRequisicion"""

    ESTADOS = {
        "BORRADOR": "borrador",
        "SOLICITADO": "Solicitado",
        "AUTORIZADO": "Autorizado",
        "REVISADO": "Revisado",
        "ENTREGADO": "Entregado",
    }

    # Nombre de la tabla
    __tablename__ = "req_requisiciones"

    # Clave primaria
    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)

    # Clave foránea
    usuario_id: Mapped[int] = mapped_column(ForeignKey("usuarios.id"))
    usuario: Mapped["Usuario"] = relationship(back_populates="req_requisiciones")

    # Columnas
    fecha: Mapped[date] = mapped_column(Date, default=now())
    gasto: Mapped[str] = mapped_column(String(32))
    glosa: Mapped[str] = mapped_column(String(32))
    programa: Mapped[str] = mapped_column(String(128))
    fuente_financiamiento: Mapped[str] = mapped_column(String(128))
    fecha_requerida: Mapped[date] = mapped_column(Date)
    observaciones: Mapped[str] = mapped_column(String(256))
    justificacion: Mapped[str] = mapped_column(String(256))
    estado: Mapped[str] = mapped_column(Enum(*ESTADOS, name="req_requisiciones_estados", native_enum=False), index=True)
    esta_archivado: Mapped[bool] = mapped_column(default=False)
    esta_cancelado: Mapped[bool] = mapped_column(default=False)

    # El folio es None cuando el estado es BORRADOR
    # Cuando se firma el documento, se genera un folio y se separa su año y número
    folio: Mapped[Optional[str]] = mapped_column(String(64))
    folio_anio: Mapped[Optional[int]]
    folio_num: Mapped[Optional[int]]

    # Columnas firma electrónica simple
    firma_simple: Mapped[str] = mapped_column(String(256), default="")
    firma_simple_tiempo: Mapped[Optional[datetime]]

    # Columnas autorizo (Usuarios)
    autorizo_id: Mapped[int]
    autorizo_tiempo: Mapped[Optional[datetime]]

    # Columnas reviso (Usuarios)
    reviso_id: Mapped[int]
    reviso_tiempo: Mapped[Optional[datetime]]

    # Hijos
    req_requisiciones_registros: Mapped[List["ReqRequisicionRegistro"]] = relationship(back_populates="req_requisicion")

    def __repr__(self):
        """Representación"""
        return f"<ReqRequisicion {self.id}>"
