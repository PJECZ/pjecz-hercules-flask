"""
Ofi Documentos Destinatarios, formularios
"""

from flask_wtf import FlaskForm
from wtforms import StringField, SubmitField, SelectField
from wtforms.validators import DataRequired, Length, Optional


class OfiDocumentoDestinatarioForm(FlaskForm):
    """Formulario OfiDocumentoDestinatario"""

    ofi_documento = StringField("Oficio")  # Read-Only
    usuario = SelectField("Usuario", coerce=int, validate_choice=False, validators=[DataRequired()])
    guardar = SubmitField("Guardar")
