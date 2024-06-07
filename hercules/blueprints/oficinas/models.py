"""
Oficinas, modelos
"""

from sqlalchemy import Boolean, Column, ForeignKey, Integer, String, Time
from sqlalchemy.orm import relationship

from lib.universal_mixin import UniversalMixin

from hercules.extensions import database


class Oficina(database.Model, UniversalMixin):
    """Oficina"""

    TIPOS = {
        "NO DEFINIDO": "NO DEFINIDO",
        "O.J. DE 1RA. INSTANCIA": "O.J. DE 1RA. INSTANCIA",
        "O.J. DE 2DA. INSTANCIA": "O.J. DE 2DA. INSTANCIA",
        "ADMINISTRATICO Y/O U. ADMIN.": "ADMINISTRATICO Y/O U. ADMIN.",
    }

    # Nombre de la tabla
    __tablename__ = "oficinas"

    # Clave primaria
    id = Column(Integer, primary_key=True)

    # Claves foráneas
    distrito_id = Column(Integer, ForeignKey("distritos.id"), index=True, nullable=False)
    distrito = relationship("Distrito", back_populates="oficinas")
    domicilio_id = Column(Integer, ForeignKey("domicilios.id"), index=True, nullable=False)
    domicilio = relationship("Domicilio", back_populates="oficinas")

    # Columnas
    clave = Column(String(32), unique=True, nullable=False)
    descripcion = Column(String(512), nullable=False)
    descripcion_corta = Column(String(64), nullable=False)
    es_jurisdiccional = Column(Boolean, nullable=False, default=False)
    apertura = Column(Time(), nullable=False)
    cierre = Column(Time(), nullable=False)
    limite_personas = Column(Integer, nullable=False)
    telefono = Column(String(48), nullable=False)
    extension = Column(String(24), nullable=False)

    # Hijos
    usuarios = relationship("Usuario", back_populates="oficina")

    def __repr__(self):
        """Representación"""
        return f"<Oficina {self.id}>"
