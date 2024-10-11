"""
Edictos, formularios
"""

from flask_wtf import FlaskForm
from flask_wtf.file import FileRequired
from wtforms import BooleanField, DateField, FileField, StringField, SubmitField
from wtforms.validators import DataRequired, Length, Optional, Regexp

from lib.safe_string import EXPEDIENTE_REGEXP, NUMERO_PUBLICACION_REGEXP


class EdictoNewForm(FlaskForm):
    """Formulario Edicto"""

    distrito = StringField("Distrito")  # Read only
    autoridad = StringField("Autoridad")  # Read only
    fecha = DateField("Fecha", validators=[DataRequired()])
    descripcion = StringField("Descripcion", validators=[DataRequired(), Length(max=256)])
    expediente = StringField("Expediente", validators=[Optional(), Length(max=16), Regexp(EXPEDIENTE_REGEXP)])
    numero_publicacion = StringField(
        "No. de publicación", validators=[Optional(), Length(max=16), Regexp(NUMERO_PUBLICACION_REGEXP)]
    )
    archivo = FileField("Archivo PDF", validators=[FileRequired()])
    es_declaracion_de_ausencia = BooleanField("Es Declaración de Ausencia", validators=[Optional()])
    guardar = SubmitField("Guardar")


class EdictoEditForm(FlaskForm):
    """Formulario para editar Edicto"""

    fecha = DateField("Fecha", validators=[DataRequired()])
    descripcion = StringField("Descripcion", validators=[DataRequired(), Length(max=256)])
    expediente = StringField("Expediente", validators=[Optional(), Length(max=16), Regexp(EXPEDIENTE_REGEXP)])
    numero_publicacion = StringField(
        "No. de publicación", validators=[Optional(), Length(max=16), Regexp(NUMERO_PUBLICACION_REGEXP)]
    )
    es_declaracion_de_ausencia = BooleanField("Es Declaración de Ausencia", validators=[Optional()])
    guardar = SubmitField("Guardar")
