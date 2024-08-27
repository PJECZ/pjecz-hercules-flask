"""
Inventarios Equipos Fotos, formularios
"""

from flask_wtf import FlaskForm
from flask_wtf.file import FileRequired
from wtforms import FileField, StringField, SubmitField
from wtforms.validators import DataRequired, Length


class InvEquipoFotoForm(FlaskForm):
    """Formulario InvEquipoFoto"""

    descripcion = StringField("Descripción del archivo", validators=[DataRequired()])
    archivo = FileField("Archivo de imagen", validators=[FileRequired()])
    guardar = SubmitField("Guardar")
