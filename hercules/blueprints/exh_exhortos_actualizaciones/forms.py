"""
Exh Exhortos Actualizaciones, formularios
"""

from flask_wtf import FlaskForm
from wtforms import SelectField, StringField, SubmitField, TextAreaField
from wtforms.validators import DataRequired, Length, Optional

TIPOS_ACTUALIZACIONES = [
    ("AreaTurnado", "Área de Turnado"),
    ("NumeroExhorto", "Número de Exhorto"),
]


class ExhExhortoActualizacionForm(FlaskForm):
    """Formulario para agregar una actualización de un exhorto"""

    # exh_exhorto_exhorto_origen_id = StringField("Exhorto Origen ID")  # Read only
    origen_id = StringField("Origen ID")  # Read only
    tipo_actualizacion = SelectField("Tipo de Actualización", validators=[DataRequired()], choices=TIPOS_ACTUALIZACIONES)
    descripcion = TextAreaField("Descripción", validators=[DataRequired(), Length(max=256)])
    guardar = SubmitField("Guardar")
