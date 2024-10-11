"""
Glosas, modelos
"""

from datetime import date

from sqlalchemy import Date, Enum, ForeignKey, String
from sqlalchemy.orm import Mapped, mapped_column, relationship

from hercules.extensions import database
from lib.universal_mixin import UniversalMixin


class Glosa(database.Model, UniversalMixin):
    """Glosa"""

    TIPOS_JUICIOS = {
        "ND": "No Definido",
        "AMPARO": "Amparo",
        "EJECUCION": "Ejecución",
        "JUICIO ORAL": "Juicio Oral",
        "JUICIO DE NULIDAD": "Juicio de Nulidad",
        "LABORAL LAUDO": "Laboral Laudo",
        "ORAL": "Oral",
        "PENAL": "Penal",
        "SALA CIVIL": "Sala Civil",
        "SALA CIVIL Y FAMILIAR": "Sala Civil y Familiar",
        "TRADICIONAL": "Tradicional",
    }

    # Nombre de la tabla
    __tablename__ = "glosas"

    # Clave primaria
    id: Mapped[int] = mapped_column(primary_key=True)

    # Clave foránea
    autoridad_id: Mapped[int] = mapped_column(ForeignKey("autoridades.id"))
    autoridad: Mapped["Autoridad"] = relationship(back_populates="glosas")

    # Columnas
    fecha: Mapped[date] = mapped_column(Date(), index=True)
    tipo_juicio: Mapped[str] = mapped_column(Enum(*TIPOS_JUICIOS, name="glosas_tipos_juicios", native_enum=False), index=True)
    descripcion: Mapped[str] = mapped_column(String(256))
    expediente: Mapped[str] = mapped_column(String(16))
    archivo: Mapped[str] = mapped_column(String(256), default="", server_default="")
    url: Mapped[str] = mapped_column(String(512), default="", server_default="")

    @property
    def descargar_url(self):
        """URL para descargar el archivo desde el sitio web"""
        if self.id:
            return f"https://www.pjecz.gob.mx/consultas/glosas/descargar/?id={self.id}"
        return ""

    def __repr__(self):
        """Representación"""
        return f"<Glosa {self.id}"
