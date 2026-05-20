"""
VASPEC Digitalizaciones, formularios
"""

from flask_wtf import FlaskForm
from wtforms import StringField, SubmitField, TextAreaField
from wtforms.validators import Length, Optional


class VspDigitalizacionForm(FlaskForm):
    """Formulario VspDigitalizacionForm"""

    descripcion = StringField("Descripción", validators=[Optional(), Length(max=256)])
    observaciones = TextAreaField("Observaciones", validators=[Optional(), Length(max=1000)], render_kw={"rows": 6})
    guardar = SubmitField("Guardar")
