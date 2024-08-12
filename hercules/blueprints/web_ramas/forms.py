"""
Web Ramas, formularios
"""

from flask_wtf import FlaskForm
from wtforms import StringField, SubmitField
from wtforms.validators import DataRequired, Length


class WebRamaForm(FlaskForm):
    """Formulario WebRama"""

    nombre = StringField("Nombre", validators=[DataRequired(), Length(max=256)])
    clave = StringField("Clave", validators=[DataRequired(), Length(max=16)])
    guardar = SubmitField("Guardar")
