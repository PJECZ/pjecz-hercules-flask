"""
Ofi Documentos, formularios
"""

from flask_wtf import FlaskForm
from wtforms import StringField, SubmitField, TextAreaField, IntegerField
from wtforms.validators import DataRequired, Length, Optional


class OfiDocumentoForm(FlaskForm):
    """Formulario OfiDocumento"""

    titulo = StringField("Título", validators=[DataRequired(), Length(max=256)])
    folio = IntegerField("Folio", validators=[Optional()])
    contenido = TextAreaField("Contenido", validators=[DataRequired()])
    guardar = SubmitField("Guardar")
