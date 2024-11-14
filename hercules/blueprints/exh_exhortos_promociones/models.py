"""
Exhortos - Promociones, modelos
"""

from datetime import datetime
from typing import List, Optional

from sqlalchemy import DateTime, ForeignKey, String
from sqlalchemy.orm import Mapped, mapped_column, relationship
from sqlalchemy.sql.functions import now

from lib.universal_mixin import UniversalMixin
from hercules.extensions import database


class ExhExhortoPromocion(database.Model, UniversalMixin):
    """ExhExhortoPromocion"""

    # Nombre de la tabla
    __tablename__ = "exh_exhortos_promociones"

    # Clave primaria
    id: Mapped[int] = mapped_column(primary_key=True)

    # Clave foránea
    exh_exhorto_id: Mapped[int] = mapped_column(ForeignKey("exh_exhortos.id"))
    exh_exhorto: Mapped["ExhExhorto"] = relationship(back_populates="exh_exhortos_promociones")

    # Columnas
    # Identificador del origen de la promoción; éste puede ser el folio del oficio u otro documento desde donde partió la promoción
    folio_origen_promocion: Mapped[str] = mapped_column(String(16), unique=True)

    # Hijo: Contiene la definición de los promoventes, en este caso el juzgado quien realiza la promoción
    # exh_promoventes: Mapped[List["ExhExhortosParte"]] = relationship(back_populates="exh_promocion")

    # Número de fojas que contiene la promoción.
    # El valor 0 significa "No Especificado".
    fojas: Mapped[int]

    # Fecha y hora en que el Poder Judicial promovente registró que se envió la promoción en su hora local.
    # En caso de no enviar este dato, el Poder Judicial promovido puede tomar su fecha hora local.
    fecha_orgien: Mapped[Optional[datetime]] = mapped_column(DateTime, default=now())

    # Texto simple que contenga información extra o relevante sobre el exhorto.
    observaciones: Mapped[Optional[str]] = mapped_column(String(1024))

    # Hijo: Colección de los datos referentes a los archivos que se van a recibir el Poder Judicial exhortado en el envío del Exhorto.
    # exh_archivos: Mapped[List["ExhExhortosArchivo"]] = relationship(back_populates="exh_promocion")

    def __repr__(self):
        """Representación"""
        return f"<ExhExhortoPromocion {self.id}>"