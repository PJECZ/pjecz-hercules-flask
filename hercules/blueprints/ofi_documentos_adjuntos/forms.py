"""
Ofi Documentos Adjuntos, formularios
"""

from flask_wtf import FlaskForm
from wtforms import StringField, SubmitField, FileField
from wtforms.validators import DataRequired, Length, Optional


class OfiDocumentoAdjuntoForm(FlaskForm):
    """Formulario OfiDocumentoAdjunto"""

    ofi_documento = StringField("Oficio descripción")  # Read-Only
    descripcion = StringField("Descripción", validators=[DataRequired(), Length(max=256)])
    archivo = FileField("Archivo", validators=[DataRequired()])
    guardar = SubmitField("Guardar")
