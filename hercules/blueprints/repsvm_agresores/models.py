"""
REPSVM Agresores, modelos
"""

from typing import List, Optional

from sqlalchemy import Enum, ForeignKey, String
from sqlalchemy.orm import Mapped, mapped_column, relationship

from hercules.extensions import database
from lib.universal_mixin import UniversalMixin


class REPSVMAgresor(database.Model, UniversalMixin):
    """REPSVMAgresor"""

    TIPOS_JUZGADOS = {
        "ND": "No Definido",
        "JUZGADO ESPECIALIZADO EN VIOLENCIA CONTRA LAS MUJERES": "Juzgado Especializado en Violencia contra las Mujeres",
        "JUZGADO ESPECIALIZADO EN VIOLENCIA FAMILIAR": "Juzgado Especializado en Violencia Familiar",
        "JUZGADO DE PRIMERA INSTANCIA EN MATERIA PENAL": "Juzgado de Primera Instancia en Materia Penal",
    }

    TIPOS_SENTENCIAS = {
        "ND": "No Definido",
        "PROCEDIMIENTO ABREVIADO": "Procedimiento Abreviado",
        "JUICIO ORAL": "Juicio Oral",
    }

    # Nombre de la tabla
    __tablename__ = "repsvm_agresores"

    # Clave primaria
    id: Mapped[int] = mapped_column(primary_key=True)

    # Clave foránea
    distrito_id: Mapped[int] = mapped_column(ForeignKey("distritos.id"))
    distrito: Mapped["Distrito"] = relationship(back_populates="repsvm_agresores")

    # Columnas
    consecutivo: Mapped[int]
    delito_generico: Mapped[str] = mapped_column(String(256))
    delito_especifico: Mapped[str] = mapped_column(String(1024))
    es_publico: Mapped[bool] = mapped_column(default=False)
    nombre: Mapped[str] = mapped_column(String(256))
    numero_causa: Mapped[str] = mapped_column(String(256))
    pena_impuesta: Mapped[str] = mapped_column(String(256))
    observaciones: Mapped[Optional[str]] = mapped_column(String(1024))
    sentencia_url: Mapped[Optional[str]] = mapped_column(String(512))
    tipo_juzgado: Mapped[str] = mapped_column(Enum(*TIPOS_JUZGADOS, name="tipos_juzgados", native_enum=False), index=True)
    tipo_sentencia: Mapped[str] = mapped_column(Enum(*TIPOS_SENTENCIAS, name="tipos_juzgados", native_enum=False), index=True)

    # Hijos
    repsvm_agresores_delitos: Mapped[List["REPSVMAgresorDelito"]] = relationship(back_populates="repsvm_agresor")

    def __repr__(self):
        """Representación"""
        return f"<REPSVMAgresor {self.id}>"
