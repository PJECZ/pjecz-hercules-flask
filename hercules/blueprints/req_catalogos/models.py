"""
Requisiciones Catálogos, modelos
"""

from typing import List, Optional

from sqlalchemy import Enum, ForeignKey, String
from sqlalchemy.orm import Mapped, mapped_column, relationship

from lib.universal_mixin import UniversalMixin
from hercules.extensions import database


class ReqCatalogo(database.Model, UniversalMixin):
    """ReqCatalogo"""

    UNIDADES_MEDIDAS = {
        "METROS": "Metros",
        "KILOGRAMOS": "Kilogramos",
        "GRAMOS": "Gramos",
        "PIEZA": "Pieza",
        "LITROS": "Litros",
    }

    # Nombre de la tabla
    __tablename__ = "req_catalogos"

    # Clave foránea
    req_categoria_id: Mapped[int] = mapped_column(ForeignKey("req_categorias.id"))
    req_categoria: Mapped["ReqCategoria"] = relationship(back_populates="req_catalogos")

    # Clave primaria
    id: Mapped[int] = mapped_column(primary_key=True)

    # Columnas
    clave: Mapped[str] = mapped_column(String(16), unique=True)
    descripcion: Mapped[str] = mapped_column(String(256))
    unidad_medida: Mapped[str] = mapped_column(
        Enum(*UNIDADES_MEDIDAS, name="req_catalogos_unidades_medidas", native_enum=False), index=True
    )

    # Hijos
    req_requisiciones_registros: Mapped[List["ReqRequisicionRegistro"]] = relationship(back_populates="req_catalogo")

    @property
    def clave_descripcion(self):
        """Junta clave y descripcion"""
        return self.clave + ": " + self.descripcion

    @property
    def unidad_medida_descripcion(self):
        """Descripción de las unidades de medida"""
        return self.unidad_medida + ": " + self.UNIDADES_MEDIDAS[self.unidad_medida]

    def __repr__(self):
        """Representación"""
        return f"<ReqCatalogo {self.id}>"
