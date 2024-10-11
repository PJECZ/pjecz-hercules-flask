"""
Glosas, formularios
"""

from flask_wtf import FlaskForm
from flask_wtf.file import FileRequired
from wtforms import DateField, FileField, SelectField, StringField, SubmitField
from wtforms.validators import DataRequired, Length, Regexp

from hercules.blueprints.glosas.models import Glosa
from lib.safe_string import EXPEDIENTE_REGEXP


class GlosaNewForm(FlaskForm):
    """Formulario para una nueva Glosa"""

    distrito = StringField("Distrito")  # Read only
    autoridad = StringField("Autoridad")  # Read only
    fecha = DateField("Fecha", validators=[DataRequired()])
    tipo_juicio = SelectField("Tipo de juicio", choices=Glosa.TIPOS_JUICIOS.items())
    descripcion = StringField("Descripción", validators=[DataRequired(), Length(max=64)])
    expediente = StringField("Expediente", validators=[DataRequired(), Length(max=16), Regexp(EXPEDIENTE_REGEXP)])
    archivo = FileField("Archivo PDF", validators=[FileRequired()])
    guardar = SubmitField("Guardar")


class GlosaEditForm(FlaskForm):
    """Formulario para editar una Glosa"""

    fecha = DateField("Fecha", validators=[DataRequired()])
    tipo_juicio = SelectField("Tipo de juicio", choices=Glosa.TIPOS_JUICIOS.items())
    descripcion = StringField("Descripción", validators=[DataRequired(), Length(max=64)])
    expediente = StringField("Expediente", validators=[DataRequired(), Length(max=16), Regexp(EXPEDIENTE_REGEXP)])
    guardar = SubmitField("Guardar")
