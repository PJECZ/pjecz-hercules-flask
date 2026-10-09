"""
DGT Tipos, formularios
"""

from flask_wtf import FlaskForm
from wtforms import StringField, SubmitField
from wtforms.validators import DataRequired, Length


class DgtTipoForm(FlaskForm):
    """Formulario DgtTipo"""

    clave = StringField("Clave", validators=[DataRequired(), Length(max=64)])
    descripcion = StringField("Descripción", validators=[DataRequired(), Length(max=256)])
    guardar = SubmitField("Guardar")
