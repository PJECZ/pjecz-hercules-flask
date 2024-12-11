"""
Bitácoras de APIs
"""

from typing import Optional

from sqlalchemy import JSON, Enum, ForeignKey, String
from sqlalchemy.orm import Mapped, mapped_column, relationship

from hercules.extensions import database
from lib.universal_mixin import UniversalMixin


class BitacoraAPI(database.Model, UniversalMixin):
    """BitacoraAPI"""

    OPERACIONES = {
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
    ruta: Mapped[str] = mapped_column(String(512))
    operacion: Mapped[str] = mapped_column(Enum(*OPERACIONES, name="operaciones_tipos", native_enum=False), index=True)
    descripcion: Mapped[str] = mapped_column(String(256))
    datos: Mapped[Optional[dict]] = mapped_column(JSON)

    def __repr__(self):
        """Representación"""
        return f"<Bitacora API {self.creado} {self.descripcion}>"
