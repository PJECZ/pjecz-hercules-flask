"""
Web Paginas, modelos
"""

from datetime import datetime
from typing import List, Optional

from sqlalchemy import Date, Enum, ForeignKey, String, Text
from sqlalchemy.orm import Mapped, mapped_column, relationship

from hercules.extensions import database
from lib.universal_mixin import UniversalMixin


class WebPagina(database.Model, UniversalMixin):
    """WebPagina"""

    ESTADOS = {
        "BORRADOR": "BORRADOR",
        "PUBLICAR": "PUBLICAR",
    }

    # Nombre de la tabla
    __tablename__ = "web_paginas"

    # Clave primaria
    id: Mapped[int] = mapped_column(primary_key=True)

    # Clave foránea
    web_rama_id: Mapped[int] = mapped_column(ForeignKey("web_ramas.id"))
    web_rama: Mapped["WebRama"] = relationship(back_populates="web_paginas")

    # Columnas
    titulo: Mapped[str] = mapped_column(String(256))
    clave: Mapped[str] = mapped_column(String(16), unique=True)
    fecha_modificacion: Mapped[datetime] = mapped_column(Date)
    responsable: Mapped[Optional[str]] = mapped_column(String(256))
    ruta: Mapped[str] = mapped_column(String(256))
    contenido: Mapped[str] = mapped_column(Text)
    estado: Mapped[str] = mapped_column(Enum(*ESTADOS, name="web_paginas_estados", native_enum=False), index=True)

    # Hijos
    web_archivos: Mapped[List["WebArchivo"]] = relationship("WebArchivo", back_populates="web_pagina")

    def __repr__(self):
        """Representación"""
        return f"<WebPagina {self.id}>"
