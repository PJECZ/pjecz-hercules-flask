"""
Exh Exhortos Promociones, formularios
"""

from flask_wtf import FlaskForm
from wtforms import IntegerField, StringField, SubmitField, TextAreaField
from wtforms.validators import DataRequired, Length, Optional


class ExhExhortoPromocionForm(FlaskForm):
    """Formulario para agregar o editar una promoción al exhorto"""

    folio_origen_promocion = StringField("Folio Origen Promoción", validators=[DataRequired(), Length(max=64)])
    fojas = IntegerField("Fojas", validators=[DataRequired()])
    observaciones = TextAreaField("Observaciones", validators=[Optional()])
    guardar = SubmitField("Guardar")
