"""
Bitácoras de APIs
"""

from typing import Optional

from sqlalchemy import JSONB, Boolean, Enum, ForeignKey, String
from sqlalchemy.orm import Mapped, mapped_column, relationship

from hercules.extensions import database
from lib.universal_mixin import UniversalMixin


class BitacoraAPI(database.Model, UniversalMixin):
    """BitacoraAPI"""

    HTTP_REQUESTS = {
        "GET": "GET",
        "POST": "POST",
        "PUT": "PUT",
        "DELETE": "DELETE",
    }

    # Nombre de la tabla
    __tablename__ = "bitacoras_apis"

    # Clave primaria
    id: Mapped[int] = mapped_column(primary_key=True)

    # Claves foráneas
    usuario_id: Mapped[int] = mapped_column(ForeignKey("usuarios.id"))
    usuario: Mapped["Usuario"] = relationship(back_populates="bitacoras")

    # Columnas
    api: Mapped[str] = mapped_column(String(256))
    endpoint: Mapped[str] = mapped_column(String(512))
    http_request: Mapped[str] = mapped_column(Enum(*HTTP_REQUESTS, name="http_requests_types", native_enum=False), index=True)
    success: Mapped[bool] = mapped_column(Boolean, index=True)
    message: Mapped[str] = mapped_column(String(512))
    errors: Mapped[list[str]]
    data: Mapped[list[dict]] = mapped_column(JSONB)

    def __repr__(self):
        """Representación"""
        return f"<Bitacora API {self.creado} {self.descripcion}>"
