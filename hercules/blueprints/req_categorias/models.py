"""
Requisiciones Categorias, modelos
"""

import inspect
from hercules.extensions import database
from lib.universal_mixin import UniversalMixin


class ReqCategoria(database.Model, UniversalMixin):
    """ReqCategoria"""

    # Nombre de la tabla
    __tablename__ = "req_categorias"

    # Clave primaria
    id = database.Column(database.Integer, primary_key=True)

    # Columnas
    descripcion = database.Column(database.String(256), nullable=False)

    # Hijos
    req_catalogos = database.relationship("ReqCatalogo", back_populates="req_categoria")

    def __repr__(self):
        """Representación"""
        return f"<ReqCategoria {self.id}>"

    def object_as_dict(obj):
        return {c.key: getattr(obj, c.key) for c in inspect(obj).mapper.column_attrs}
