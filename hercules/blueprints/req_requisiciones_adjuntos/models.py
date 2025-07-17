"""
Req Requisiciones Adjuntos, modelos
"""

import uuid

from sqlalchemy import ForeignKey, String
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from lib.universal_mixin import UniversalMixin
from hercules.extensions import database


class ReqRequisicionAdjunto(database.Model, UniversalMixin):
    """ReqRequisicionAdjunto"""

    EXTENSIONES = {
        "jpg": ("Imagen", "image/jpg"),
        "jpeg": ("Imagen", "image/jpeg"),
        "png": ("Imagen", "image/png"),
        "pdf": ("Archivo PDF", "application/pdf"),
        "docx": ("Archivo Word", "application/msword"),
        "xlsx": ("Archivo Excel", "application/vnd.ms-excel"),
    }

    # Nombre de la tabla
    __tablename__ = "req_requisiciones_adjuntos"

    # Clave primaria
    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)

    # Clave foránea
    req_requisicion_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("req_requisiciones.id"))
    req_requisicion: Mapped["ReqRequisicion"] = relationship(back_populates="req_requisiciones_adjuntos")

    # Columnas
    descripcion: Mapped[str] = mapped_column(String(256))
    archivo: Mapped[str] = mapped_column(String(256), default="")
    url: Mapped[str] = mapped_column(String(512), default="")

    # Variables
    extension = ""

    @staticmethod
    def type_format(file_name):
        "Tipo de formato del archivo"
        try:
            extension = file_name.rsplit(".", 1)[1]
        except:
            return ""
        if extension in ("jpg", "jpeg", "png"):
            return "IMG"
        if extension in ("docx", "xlsx"):
            return "DOC"
        if extension == "pdf":
            return "PDF"
        return ""

    def set_extension(self, archivo_nombre):
        """Establece el tipo de extensión del archivo"""
        extensiones_permitidas = ReqRequisicionAdjunto.EXTENSIONES.keys()
        if "." in archivo_nombre and archivo_nombre.rsplit(".", 1)[1] in extensiones_permitidas:
            self.extension = archivo_nombre.rsplit(".", 1)[1]
            return True
        return False

    def __repr__(self):
        """Representación"""
        return f"<ReqRequisicionAdjunto {self.id}>"
