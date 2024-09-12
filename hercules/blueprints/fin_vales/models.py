"""
Financieros Vales, modelos
"""

from datetime import datetime
from typing import Optional

from sqlalchemy import Enum, ForeignKey, String, Text
from sqlalchemy.orm import Mapped, mapped_column, relationship

from hercules.extensions import database
from lib.universal_mixin import UniversalMixin


class FinVale(database.Model, UniversalMixin):
    """FinVale"""

    ESTADOS = {
        "CREADO": "Creado",  # PASO 1 Un usuario lo ha creado
        "SOLICITADO": "Solicitado",  # PASO 2 El superior lo autorizo con su firma
        "CANCELADO POR SOLICITANTE": "Cancelado por solicitante",  # El superior ha cancelado la firma
        "AUTORIZADO": "Autorizado",  # PASO 3 Finanzas lo autorizo
        "CANCELADO POR AUTORIZANTE": "Cancelado por autorizante",  # Finanzas ha cancelado la firma
        "ENTREGADO": "Entregado",  # PASO 4 El usuario lo recogió
        "POR REVISAR": "Por revisar",  # PASO 5 El usuario a subido los archivos adjuntos
        "ARCHIVADO": "Archivado",  # PASO 6 Finanzas lo archiva si cumple con la evidencia
    }

    TIPOS = {
        "NO DEFINIDO": "No definido",
        "GASOLINA": "Gasolina",
    }

    # Nombre de la tabla
    __tablename__ = "fin_vales"

    # Clave primaria
    id: Mapped[int] = mapped_column(primary_key=True)

    # Clave foránea
    usuario_id: Mapped[int] = mapped_column(ForeignKey("usuarios.id"))
    usuario: Mapped["Usuario"] = relationship(back_populates="fin_vales")

    # Columnas (step 1 create) estado CREADO
    estado: Mapped[str] = mapped_column(Enum(*ESTADOS, name="fin_vales_estados", native_enum=False), index=True)
    tipo: Mapped[str] = mapped_column(Enum(*TIPOS, name="fin_vales_tipos", native_enum=False), index=True)
    justificacion: Mapped[str] = mapped_column(Text())
    monto: Mapped[float]

    # Columnas (step 2 request) estado SOLICITADO
    solicito_nombre: Mapped[Optional[str]] = mapped_column(String(256))
    solicito_puesto: Mapped[Optional[str]] = mapped_column(String(256))
    solicito_email: Mapped[Optional[str]] = mapped_column(String(256))
    solicito_efirma_tiempo: Mapped[Optional[datetime]]
    solicito_efirma_folio: Mapped[Optional[int]]
    solicito_efirma_sello_digital: Mapped[Optional[str]] = mapped_column(String(256))
    solicito_efirma_url: Mapped[Optional[str]] = mapped_column(String(256))
    solicito_efirma_qr_url: Mapped[Optional[str]] = mapped_column(String(256))
    solicito_efirma_mensaje: Mapped[Optional[str]] = mapped_column(String(512))
    solicito_efirma_error: Mapped[Optional[str]] = mapped_column(String(512))

    # Columnas (cancel 2 request) estado CANCELADO POR SOLICITANTE
    solicito_cancelo_tiempo: Mapped[Optional[datetime]]
    solicito_cancelo_motivo: Mapped[Optional[str]] = mapped_column(String(256))
    solicito_cancelo_error: Mapped[Optional[str]] = mapped_column(String(512))

    # Columnas (step 3 authorize) estado AUTORIZADO
    autorizo_nombre: Mapped[Optional[str]] = mapped_column(String(256))
    autorizo_puesto: Mapped[Optional[str]] = mapped_column(String(256))
    autorizo_email: Mapped[Optional[str]] = mapped_column(String(256))
    autorizo_efirma_tiempo: Mapped[Optional[datetime]]
    autorizo_efirma_folio: Mapped[Optional[int]]
    autorizo_efirma_sello_digital: Mapped[Optional[str]] = mapped_column(String(256))
    autorizo_efirma_url: Mapped[Optional[str]] = mapped_column(String(256))
    autorizo_efirma_qr_url: Mapped[Optional[str]] = mapped_column(String(256))
    autorizo_efirma_mensaje: Mapped[Optional[str]] = mapped_column(String(512))
    autorizo_efirma_error: Mapped[Optional[str]] = mapped_column(String(512))

    # Columnas (cancel 3 authorize) estado CANCELADO POR AUTORIZANTE
    autorizo_cancelo_tiempo: Mapped[Optional[datetime]]
    autorizo_cancelo_motivo: Mapped[Optional[str]] = mapped_column(String(256))
    autorizo_cancelo_error: Mapped[Optional[str]] = mapped_column(String(512))

    # Columnas (step 4 deliver) estado ENTREGADO
    folio: Mapped[Optional[int]]

    # Columnas (step 5 attachments) estado POR REVISAR
    vehiculo_descripcion: Mapped[Optional[str]] = mapped_column(String(256))
    tanque_inicial: Mapped[Optional[str]] = mapped_column(String(48))
    tanque_final: Mapped[Optional[str]] = mapped_column(String(48))
    kilometraje_inicial: Mapped[Optional[int]]
    kilometraje_final: Mapped[Optional[int]]

    # Columnas (step 6 archive) estado ARCHIVADO
    notas: Mapped[Optional[str]] = mapped_column(String(1024))

    def __repr__(self):
        """Representación"""
        return f"<FinVale {self.clave}>"
