"""
Inventarios Componentes, modelos
"""

from typing import Optional

from sqlalchemy import Enum, ForeignKey, String
from sqlalchemy.orm import Mapped, mapped_column, relationship

from hercules.extensions import database
from lib.universal_mixin import UniversalMixin


class InvComponente(database.Model, UniversalMixin):
    """InvComponente"""

    GENERACIONES = {
        "NO DEFINIDO": "No definido",
        "2da Gen": "Segunda",
        "3er Gen": "Tercera",
        "4ta Gen": "Cuarta",
        "5ta Gen": "Quinta",
        "6ta Gen": "Sexta",
        "7ma Gen": "Septima",
        "8va Gen": "Octava",
        "9na Gen": "Novena",
        "10ma Gen": "Decima",
        "11va Gen": "Onceava",
        "12va Gen": "Doceava",
    }

    # Nombre de la tabla
    __tablename__ = "inv_componentes"

    # Clave primaria
    id: Mapped[int] = mapped_column(primary_key=True)

    # Claves foráneas
    inv_categoria_id: Mapped[int] = mapped_column(ForeignKey("inv_categorias.id"))
    inv_categoria: Mapped["InvCategoria"] = relationship(back_populates="inv_componentes")
    inv_equipo_id: Mapped[int] = mapped_column(ForeignKey("inv_equipos.id"))
    inv_equipo: Mapped["InvEquipo"] = relationship(back_populates="inv_componentes")

    # Columnas
    descripcion: Mapped[str] = mapped_column(String(256))
    cantidad: Mapped[int]
    generacion: Mapped[str] = mapped_column(
        Enum(*GENERACIONES, name="inv_componentes_generaciones", native_enum=False),
        index=True,
        default="NO DEFINIDO",
    )
    version: Mapped[Optional[str]] = mapped_column(String(256))

    def __repr__(self):
        """Representación"""
        return f"<InvComponente {self.id}>"
