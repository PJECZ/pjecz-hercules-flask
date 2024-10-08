"""
Requisiciones registros, modelos
"""
from collections import OrderedDict
from hercules.extensions import database
from lib.universal_mixin import UniversalMixin


class ReqRequisicionRegistro(database.Model, UniversalMixin):
    """ReqRequisionRegistro"""

    CLAVES = OrderedDict(
        [
            ("INS", "INSUFICIENCIA"),
            ("REP", "REPOSICION DE BIENES"),
            ("OBS", "OBSOLESENCIA"),
            ("AMP", "AMPLIACION COBERTURA DEL SERVICIO"),
            ("NUE", "NUEVO PROYECTO"),
        ]
    )

    # Nombre de la tabla
    __tablename__ = "req_requisiciones_registros"

    # Clave primaria
    id = database.Column(database.Integer, primary_key=True)

    # Claves foráneas
    req_catalogo_id = database.Column(database.Integer, database.ForeignKey("req_catalogos.id"), index=True, nullable=False)
    req_catalogo = database.relationship("ReqCatalogo", back_populates="req_requisiciones_registros")
    req_requisicion_id = database.Column(database.Integer, database.ForeignKey("req_requisiciones.id"), index=True, nullable=False)
    req_requisicion = database.relationship("ReqRequisicion", back_populates="req_requisiciones_registros")

    # Columnas
    cantidad = database.Column(database.Integer, nullable=False)
    clave = database.Column(
        database.Enum(*CLAVES, name="claves", native_enum=False),
        index=True,
        nullable=False,
    )
    detalle = database.Column(database.String)

    def __repr__(self):
        """Representación"""
        return "<ReqRequisionRegistro>"
