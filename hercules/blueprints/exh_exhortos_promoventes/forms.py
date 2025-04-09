"""
Exh Exhortos Promoventes, formularios
"""

from flask_wtf import FlaskForm
from wtforms import BooleanField, RadioField, SelectField, StringField, SubmitField
from wtforms.validators import DataRequired, Length, Optional

from hercules.blueprints.exh_exhortos_promoventes.models import ExhExhortoPromovente


class ExhExhortoPromoventeForm(FlaskForm):
    """Formulario para agregar o editar un promovente"""

    nombre = StringField("Nombre", validators=[DataRequired(), Length(max=256)])
    apellido_paterno = StringField("Apellido Paterno", validators=[Optional(), Length(max=256)])
    apellido_materno = StringField("Apellido Materno", validators=[Optional(), Length(max=256)])
    genero = RadioField("Genero", coerce=str, choices=ExhExhortoPromovente.GENEROS.items(), validators=[Optional()])
    es_persona_moral = BooleanField("Es Persona Moral")
    tipo_parte = SelectField(
        "Tipo de Promovente", coerce=int, choices=ExhExhortoPromovente.TIPOS_PARTES.items(), validators=[Optional()]
    )
    tipo_parte_nombre = StringField("Tipo Promovente Nombre")
    guardar = SubmitField("Guardar")
