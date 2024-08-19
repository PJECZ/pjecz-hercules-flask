"""
Inventarios Modelos, formularios
"""

from flask_wtf import FlaskForm
from wtforms import StringField, SubmitField
from wtforms.validators import DataRequired, Length, Optional


class InvModeloForm(FlaskForm):
    """Formulario InvModelo"""

    descripcion = StringField("Descripcion", validators=[DataRequired(), Length(max=256)])
    guardar = SubmitField("Guardar")
