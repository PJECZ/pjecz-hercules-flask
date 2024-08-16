"""
Identidades Generos, formularios
"""

from flask_wtf import FlaskForm
from wtforms import DateField, SelectField, StringField, SubmitField
from wtforms.validators import DataRequired, Length, Optional, Regexp

from hercules.blueprints.identidades_generos.models import IdentidadGenero
from lib.safe_string import EXPEDIENTE_REGEXP


class IdentidadGeneroForm(FlaskForm):
    """Formulario IdentidadGenero"""

    nombre_actual = StringField("Nombre Actual", validators=[DataRequired(), Length(max=256)])
    nombre_anterior = StringField("Nombre Anterior", validators=[DataRequired(), Length(max=256)])
    fecha_nacimiento = DateField("Fecha de Nacimiento", validators=[DataRequired()])
    lugar_nacimiento = StringField("Lugar de Nacimiento", validators=[Optional()])
    genero_anterior = SelectField("Género Anterior", choices=IdentidadGenero.GENEROS.items(), validators=[DataRequired()])
    genero_actual = SelectField("Género Actual", choices=IdentidadGenero.GENEROS.items(), validators=[DataRequired()])
    nombre_padre = StringField("Nombre Padre", validators=[DataRequired(), Length(max=256)])
    nombre_madre = StringField("Nombre Madre", validators=[DataRequired(), Length(max=256)])
    procedimiento = StringField("Procedimiento", validators=[DataRequired(), Length(max=256), Regexp(EXPEDIENTE_REGEXP)])
    guardar = SubmitField("Guardar")
