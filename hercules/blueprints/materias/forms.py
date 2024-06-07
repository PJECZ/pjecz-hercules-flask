"""
Materias, formularios
"""

from flask_wtf import FlaskForm
from wtforms import BooleanField, StringField, SubmitField, TextAreaField
from wtforms.validators import DataRequired, Length, Optional


class MateriaForm(FlaskForm):
    """Formulario Materia"""

    nombre = StringField("Nombre", validators=[DataRequired(), Length(max=64)])
    descripcion = TextAreaField("Descripción", validators=[Optional(), Length(max=1024)])
    en_sentencias = BooleanField("En Sentencias", validators=[Optional()])
    guardar = SubmitField("Guardar")
