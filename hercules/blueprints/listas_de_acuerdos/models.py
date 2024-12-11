"""
Listas de Acuerdos, modelos
"""

from datetime import date, datetime
from typing import Optional

from sqlalchemy import JSON, ForeignKey, String, Text
from sqlalchemy.orm import Mapped, mapped_column, relationship

from hercules.extensions import database
from lib.universal_mixin import UniversalMixin


class ListaDeAcuerdo(database.Model, UniversalMixin):
    """ListaDeAcuerdo"""

    # Nombre de la tabla
    __tablename__ = "listas_de_acuerdos"

    # Clave primaria
    id: Mapped[int] = mapped_column(primary_key=True)

    # Clave foránea
    autoridad_id: Mapped[int] = mapped_column(ForeignKey("autoridades.id"))
    autoridad: Mapped["Autoridad"] = relationship(back_populates="listas_de_acuerdos")

    # Columnas
    fecha: Mapped[date] = mapped_column(index=True)
    descripcion: Mapped[str] = mapped_column(String(256))
    archivo: Mapped[str] = mapped_column(String(256), default="")
    url: Mapped[str] = mapped_column(String(512), default="")

    # Columnas para análisis de datos (data analytics)
    da_tiempo: Mapped[Optional[datetime]]
    da_contenido: Mapped[Optional[dict]] = mapped_column(JSON())
    da_modelo: Mapped[Optional[str]] = mapped_column(String(256))
    da_resumen: Mapped[Optional[str]] = mapped_column(String(1024))
    da_etiquetas: Mapped[Optional[str]] = mapped_column(String(256))

    @property
    def descargar_url(self):
        """URL para descargar el archivo desde el sitio web"""
        if self.id:
            return f"https://www.pjecz.gob.mx/consultas/listas-de-acuerdos/descargar/?id={self.id}"
        return ""

    def __repr__(self):
        """Representación"""
        return f"<ListaDeAcuerdo {self.id}>"
