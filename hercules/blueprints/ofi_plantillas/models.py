"""
Ofi Plantillas, modelos
"""

from typing import List, Optional

from sqlalchemy import Enum, String, Text
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import Mapped, mapped_column, relationship
from sqlalchemy.sql.functions import now

from lib.universal_mixin import UniversalMixin
from hercules.extensions import database


class OfiPlantilla(database.Model, UniversalMixin):
    """ OfiPlantilla """

    ESTADOS = {
        "HABILITADO": "Habilitado",
        "DESHABILITADO": "Deshabilitado",
    }

    # Nombre de la tabla
    __tablename__ = 'ofi_plantillas'

    # Clave primaria
    id: Mapped[int] = mapped_column(primary_key=True)

    # Columnas
    nombre: Mapped[str] = mapped_column(String(256))
    descripcion: Mapped[str] = mapped_column(String(256))
    contenido: Mapped[str] = mapped_column(Text)
    variables: Mapped[Optional[JSONB]] = mapped_column(JSONB)
    estado: Mapped[str] = mapped_column(Enum(*ESTADOS, name="ofi_plantillas_estados", native_enum=False), index=True)

    # Hijos
    ofi_documentos: Mapped[List["OfiDocumento"]] = relationship(back_populates="ofi_plantilla")

    def __repr__(self):
        """ Representación """
        return f'<OfiPlantilla {self.id}>'
