"""
Domicilios, modelos
"""

from sqlalchemy import Column, ForeignKey, Integer, String
from sqlalchemy.orm import relationship

from lib.universal_mixin import UniversalMixin

from hercules.extensions import database


class Domicilio(database.Model, UniversalMixin):
    """Domicilio"""

    # Nombre de la tabla
    __tablename__ = "domicilios"

    # Clave primaria
    id = Column(Integer, primary_key=True)

    # Clave foránea
    distrito_id = Column(Integer, ForeignKey("distritos.id"), index=True, nullable=False)
    distrito = relationship("Distrito", back_populates="domicilios")

    # Columnas
    edificio = Column(String(64), nullable=False, unique=True)
    estado = Column(String(64), nullable=False)
    municipio = Column(String(64), nullable=False)
    calle = Column(String(256), nullable=False)
    num_ext = Column(String(24), nullable=False)
    num_int = Column(String(24), nullable=False)
    colonia = Column(String(256), nullable=False)
    cp = Column(Integer(), nullable=False)
    completo = Column(String(1024), nullable=False)

    # Hijos
    oficinas = relationship("Oficina", back_populates="domicilio")

    def elaborar_completo(self):
        """Elaborar completo"""
        elementos = []
        if self.calle and self.num_ext and self.num_int:
            elementos.append(f"{self.calle} #{self.num_ext}-{self.num_int}")
        elif self.calle and self.num_ext:
            elementos.append(f"{self.calle} #{self.num_ext}")
        elif self.calle:
            elementos.append(self.calle)
        if self.colonia:
            elementos.append(self.colonia)
        if self.municipio:
            elementos.append(self.municipio)
        if self.estado and self.cp > 0:
            elementos.append(f"{self.estado}, C.P. {self.cp}")
        elif self.estado:
            elementos.append(self.estado)
        return ", ".join(elementos)

    def __repr__(self):
        """Representación"""
        return f"<Domicilio {self.id}>"
