"""
Inventarios Redes, formularios
"""

from flask_wtf import FlaskForm
from wtforms import SelectField, StringField, SubmitField
from wtforms.validators import DataRequired, Length

from hercules.blueprints.inv_redes.models import InvRed


class InvRedForm(FlaskForm):
    """Formulario InvRed"""

    nombre = StringField("Nombre", validators=[DataRequired(), Length(max=256)])
    tipo = SelectField("Tipo", choices=InvRed.TIPOS.items(), validators=[DataRequired()])
    guardar = SubmitField("Guardar")
