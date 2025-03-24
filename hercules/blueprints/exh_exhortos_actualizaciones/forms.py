"""
Exh Exhortos Actualizaciones, formularios
"""

from flask_wtf import FlaskForm
from wtforms import SelectField, StringField, SubmitField, TextAreaField
from wtforms.validators import DataRequired, Length

from hercules.blueprints.exh_exhortos_actualizaciones.models import ExhExhortoActualizacion


class ExhExhortoActualizacionForm(FlaskForm):
    """Formulario para agregar una actualización de un exhorto"""

    actualizacion_origen_id = StringField("Actualización Origen ID")  # Read only
    tipo_actualizacion = SelectField(
        "Tipo de Actualización",
        validators=[DataRequired()],
        choices=ExhExhortoActualizacion.TIPOS_ACTUALIZACIONES.items(),
    )
    descripcion = StringField("Descripción", validators=[DataRequired(), Length(max=256)])
    guardar = SubmitField("Guardar")
