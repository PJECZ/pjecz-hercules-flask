"""
Requisiciones Resguardos, modelos
"""
from typing import List

from sqlalchemy import Enum, ForeignKey, String
from sqlalchemy.orm import Mapped, mapped_column, relationship

from hercules.extensions import database
from lib.universal_mixin import UniversalMixin


class ReqResguardo(database.Model, UniversalMixin):
    """ReqResguardo"""

    # Nombre de la tabla
    __tablename__ = "req_resguardos"

    # Clave primaria
    id = database.Column(database.Integer, primary_key=True)

    # Llave foranea
    req_requisicion_id = database.Column(database.Integer, database.ForeignKey("req_requisiciones.id"), index=True, nullable=False)
    req_requisicion = database.relationship("ReqRequisicion", back_populates="req_resguardos")


    # Columnas
    archivo = database.Column(database.String(256), nullable=False)
    url = database.Column(database.String(512), nullable=False)

    def __repr__(self):
        """Representación"""
        return f"<ReqResguardo {self.id}>"
