"""
DGT Depósitos, formularios
"""

from flask_wtf import FlaskForm
from wtforms import SelectField, StringField, SubmitField
from wtforms.validators import DataRequired, Length

from hercules.blueprints.dgt_depositos.models import DgtDepositos


class DgtDepositosForm(FlaskForm):
    """Formulario DgtDepositos"""

    clave = StringField("Clave", validators=[DataRequired(), Length(max=64)])
    descripcion = StringField("Descripción", validators=[DataRequired(), Length(max=256)])
    proposito = SelectField("Propósito", choices=DgtDepositos.PROPOSITOS.items(), validators=[DataRequired()])
    guardar = SubmitField("Guardar")
