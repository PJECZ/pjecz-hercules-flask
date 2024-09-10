"""
Usuarios Nóminas, modelos
"""

from datetime import date

from sqlalchemy import ForeignKey, String
from sqlalchemy.orm import Mapped, mapped_column, relationship

from hercules.extensions import database
from lib.universal_mixin import UniversalMixin


class UsuarioNomina(database.Model, UniversalMixin):
    """UsuarioNomina"""

    # Nombre de la tabla
    __tablename__ = "usuarios_nominas"

    # Clave primaria
    id: Mapped[int] = mapped_column(primary_key=True)

    # Clave foránea
    usuario_id: Mapped[int] = mapped_column(ForeignKey("usuarios.id"))
    usuario: Mapped["Usuario"] = relationship(back_populates="usuarios_nominas")

    # Columnas
    timbrado_id: Mapped[int] = mapped_column(index=True)
    fecha: Mapped[date]
    descripcion: Mapped[str] = mapped_column(String(256))
    archivo_pdf: Mapped[str] = mapped_column(String(256), default="")
    archivo_xml: Mapped[str] = mapped_column(String(256), default="")
    url_pdf: Mapped[str] = mapped_column(String(512), default="")
    url_xml: Mapped[str] = mapped_column(String(512), default="")

    def __repr__(self):
        """Representación"""
        return f"<UsuarioNomina {self.id}>"
