"""
Inventarios Custodias, formularios
"""

from flask_wtf import FlaskForm
from wtforms import DateField, SubmitField
from wtforms.validators import DataRequired


class InvCustodiaForm(FlaskForm):
    """Formulario InvCustodia"""

    fecha = DateField("Fecha", validators=[DataRequired()])
    guardar = SubmitField("Guardar")
