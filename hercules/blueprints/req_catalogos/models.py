"""
Requisiciones Catalogos, modelos
"""
from typing import List

from sqlalchemy import Enum, ForeignKey, String, inspect
from sqlalchemy.orm import Mapped, mapped_column, relationship

from hercules.extensions import database
from lib.universal_mixin import UniversalMixin


class ReqCatalogo(database.Model, UniversalMixin):
    """ReqCatalogo"""

    # Nombre de la tabla
    __tablename__ = "req_catalogos"

    # Clave primaria
    id = database.Column(database.Integer, primary_key=True)

    # Claves foráneas
    req_categoria_id = database.Column(database.Integer, database.ForeignKey("req_categorias.id"), index=True, nullable=False)
    req_categoria = database.relationship("ReqCategoria", back_populates="req_catalogos")

    # Columnas
    codigo = database.Column(database.String(3), nullable=False, unique=True)
    descripcion = database.Column(database.String(256), nullable=False)
    unidad_medida = database.Column(database.String(50), nullable=False)
    categoria = database.Column(database.String(100), nullable=False)

    # Hijos
    req_requisiciones_registros = database.relationship("ReqRequisicionRegistro", back_populates="req_catalogo")

    def __repr__(self):
        """Representación"""
        return f"<ReqCatalogo {self.codigo}>"

    def object_as_dict(obj):
        return {c.key: getattr(obj, c.key) for c in inspect(obj).mapper.column_attrs}
