"""
Exh Exhortos Promociones, formularios
"""

from flask_wtf import FlaskForm
from wtforms import IntegerField, StringField, SubmitField, TextAreaField
from wtforms.validators import DataRequired, Length, Optional


class ExhExhortoPromocionForm(FlaskForm):
    """Formulario para agregar o editar una promoción al exhorto"""

    exh_exhorto_exhorto_origen_id = StringField("Exhorto Origen ID")  # Read only
    folio_origen_promocion = StringField("Folio Origen")  # ReadOnly
    fojas = IntegerField("Fojas", validators=[DataRequired()])
    observaciones = TextAreaField("Observaciones", validators=[Optional()])
    guardar = SubmitField("Guardar")
