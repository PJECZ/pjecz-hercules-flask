"""
Exh Exhortos Respuestas, modelos
"""

from datetime import datetime
from typing import List, Optional

from sqlalchemy import Enum, ForeignKey, String
from sqlalchemy.orm import Mapped, mapped_column, relationship

from hercules.extensions import database
from lib.universal_mixin import UniversalMixin


class ExhExhortoRespuesta(database.Model, UniversalMixin):
    """ExhExhortoRespuesta"""

    REMITENTES = {
        "INTERNO": "Interno",
        "EXTERNO": "Externo",
    }

    ESTADOS = {
        "CANCELADO": "Cancelado",
        "ENVIADO": "Enviado",
        "PENDIENTE": "Pendiente",
    }

    # Nombre de la tabla
    __tablename__ = "exh_exhortos_respuestas"

    # Clave primaria
    id: Mapped[int] = mapped_column(primary_key=True)

    # Clave foránea
    exh_exhorto_id: Mapped[int] = mapped_column(ForeignKey("exh_exhortos.id"))
    exh_exhorto: Mapped["ExhExhorto"] = relationship(back_populates="exh_exhortos_respuestas")

    # Identificador propio del Poder Judicial exhortado con el que identifica la respuesta del exhorto.
    # Este dato puede ser un número consecutivo (ej "1", "2", "3"...),
    # un GUID/UUID o cualquíer otro valor con que se identifique la respuesta
    origen_id: Mapped[Optional[str]] = mapped_column(String(48))

    # Identificador del municipio que corresponde al Juzgado/Área al que se turnó el Exhorto y que realiza la respuesta de este
    municipio_turnado_id: Mapped[Optional[int]]

    # Identificador propio del PJ exhortado que corresponde al Juzgado/Área al que se turna el Exhorto y está respondiendo
    area_turnado_id: Mapped[Optional[str]] = mapped_column(String(256))

    # Nombre del Juzgado/Área al que el Exhorto se turnó y está respondiendo.
    area_turnado_nombre: Mapped[Optional[str]] = mapped_column(String(256))

    # Número de Exhorto con el que se radicó en el Juzgado/Área que se turnó el exhorto.
    # Este número sirve para que el usuario pueda identificar su exhorto dentro del Juzgado/Área donde se turnó.
    numero_exhorto: Mapped[Optional[str]] = mapped_column(String(256))

    # Valor que representa si se realizó la diligenciación del Exhorto:
    # 0 = No Diligenciado
    # 1 = Parcialmente Diligenciado
    # 2 = Diligenciado"
    tipo_diligenciado: Mapped[Optional[int]]

    # Fecha hora local del Poder Judicial que recibe la respuesta del Exhorto
    fecha_hora_recepcion: Mapped[Optional[datetime]]

    # Texto simple referente a alguna observación u observaciones correspondientes a la respuesta del Exhorto
    observaciones: Mapped[Optional[str]] = mapped_column(String(1024))

    # Fecha hora local en el que el Poder Judicial exhortante marca la Respuesta del Exhorto como recibida
    fecha_hora_recepcion_acuse: Mapped[Optional[datetime]]

    # Si el remitente es INTERNO entonces fue creada por nosotros, si es EXTERNO fue creada por otro PJ
    remitente: Mapped[str] = mapped_column(
        Enum(*REMITENTES, name="exh_exhortos_respuestas_remitentes", native_enum=False), index=True
    )

    # Estado de la respuesta
    estado: Mapped[str] = mapped_column(Enum(*ESTADOS, name="exh_exhortos_respuestas_estados", native_enum=False), index=True)

    # Hijo
    exh_exhortos_respuestas_archivos: Mapped[List["ExhExhortoRespuestaArchivo"]] = relationship(
        back_populates="exh_exhorto_respuesta"
    )

    def __repr__(self):
        """Representación"""
        return f"<ExhExhortoRespuesta {self.id}>"
