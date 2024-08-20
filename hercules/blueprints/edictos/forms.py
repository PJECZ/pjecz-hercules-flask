"""
Edictos, formularios
"""

from flask_wtf import FlaskForm
from wtforms import DateField, StringField, SubmitField
from wtforms.validators import DataRequired, Length, Optional, Regexp

from lib.safe_string import EXPEDIENTE_REGEXP, NUMERO_PUBLICACION_REGEXP


class EdictoForm(FlaskForm):
    """Formulario Edicto"""

    distrito = StringField("Distrito")  # Read only
    autoridad = StringField("Autoridad")  # Read only
    fecha = DateField("Fecha", validators=[DataRequired()])
    descripcion = StringField("Descripcion", validators=[DataRequired(), Length(max=256)])
    expediente = StringField("Expediente", validators=[Optional(), Length(max=16), Regexp(EXPEDIENTE_REGEXP)])
    numero_publicacion = StringField(
        "No. de publicación", validators=[Optional(), Length(max=16), Regexp(NUMERO_PUBLICACION_REGEXP)]
    )
    # archivo = FileField("Archivo PDF", validators=[FileRequired()])
    guardar = SubmitField("Guardar")
