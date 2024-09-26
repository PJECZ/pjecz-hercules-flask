"""
Soportes Adjuntos Tickets, formularios
"""

from flask_wtf import FlaskForm
from flask_wtf.file import FileRequired
from wtforms import StringField, SubmitField, TextAreaField, FileField
from wtforms.validators import DataRequired, Length, Optional


class SoporteAdjuntoNewForm(FlaskForm):
    """Formulario SoporteAdjuntoNew"""

    usuario = StringField("Usuario")  # Read only
    problema = TextAreaField("Descripción del problema")  # Read only
    categoria = StringField("Categoría")  # Read only
    descripcion = StringField("Descripción del archivo", validators=[DataRequired(), Length(max=512)])
    archivo = FileField("Archivo", validators=[FileRequired()])
    guardar = SubmitField("Subir Archivo")
