"""
Ofi Plantillas, formularios
"""

from flask_wtf import FlaskForm
from wtforms import StringField, SubmitField, TextAreaField
from wtforms.validators import DataRequired, Length, Optional


class OfiPlantillaForm(FlaskForm):
    """Formulario OfiPlantilla"""

    titulo = StringField("Título", validators=[DataRequired()])
    contenido = TextAreaField("Contenido", validators=[DataRequired()])
    guardar = SubmitField("Guardar")
