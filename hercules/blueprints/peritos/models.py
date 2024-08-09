"""
Peritos, modelos
"""

from sqlalchemy import ForeignKey, String
from sqlalchemy.orm import Mapped, mapped_column, relationship

from hercules.extensions import database
from lib.universal_mixin import UniversalMixin


class Perito(database.Model, UniversalMixin):
    """Perito"""

    # Nombre de la tabla
    __tablename__ = "peritos"

    # Clave primaria
    id: Mapped[int] = mapped_column(primary_key=True)

    # Claves foráneas
    distrito_id: Mapped[int] = mapped_column(ForeignKey("distritos.id"))
    distrito: Mapped["Distrito"] = relationship(back_populates="peritos")
    perito_tipo_id: Mapped[int] = mapped_column(ForeignKey("peritos_tipos.id"))
    perito_tipo: Mapped["PeritoTipo"] = relationship(back_populates="peritos")

    # Columnas
    nombre: Mapped[str] = mapped_column(String(256))
    domicilio: Mapped[str] = mapped_column(String(256))
    telefono_fijo: Mapped[str] = mapped_column(String(64))
    telefono_celular: Mapped[str] = mapped_column(String(64))
    email: Mapped[str] = mapped_column(String(256))
    notas: Mapped[str] = mapped_column(String(256))

    @property
    def distrito_clave(self):
        """Distrito clave"""
        return self.distrito.clave

    @property
    def distrito_nombre(self):
        """Distrito nombre"""
        return self.distrito.nombre

    @property
    def distrito_nombre_corto(self):
        """Distrito nombre corto"""
        return self.distrito.nombre_corto

    @property
    def perito_tipo_nombre(self):
        """Nombre del tipo de perito"""
        return self.perito_tipo.nombre

    def __repr__(self):
        """Representación"""
        return f"<Perito {self.id}>"
