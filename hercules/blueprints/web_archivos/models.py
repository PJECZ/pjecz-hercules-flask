"""
Web Archivos, modelos
"""

from sqlalchemy import ForeignKey, String
from sqlalchemy.orm import Mapped, mapped_column, relationship

from hercules.extensions import database
from lib.universal_mixin import UniversalMixin


class WebArchivo(database.Model, UniversalMixin):
    """WebArchivo"""

    # Nombre de la tabla
    __tablename__ = "web_archivos"

    # Clave primaria
    id: Mapped[int] = mapped_column(primary_key=True)

    # Clave foránea
    web_pagina_id: Mapped[int] = mapped_column(ForeignKey("web_paginas.id"))
    web_pagina: Mapped["WebPagina"] = relationship(back_populates="web_archivos")

    # Columnas
    archivo: Mapped[str] = mapped_column(String(256))
    descripcion: Mapped[str] = mapped_column(String(256))
    url: Mapped[str] = mapped_column(String(256))

    def __repr__(self):
        """Representación"""
        return f"<WebArchivo {self.id}>"
