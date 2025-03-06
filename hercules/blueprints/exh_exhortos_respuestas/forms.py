"""
Exh Exhortos Respuestas, formularios
"""

from flask import current_app
from flask_wtf import FlaskForm
from wtforms import RadioField, SelectField, StringField, SubmitField, TextAreaField
from wtforms.validators import DataRequired, Length, Optional, Regexp

from hercules.blueprints.estados.models import Estado
from hercules.blueprints.exh_areas.models import ExhArea
from hercules.blueprints.municipios.models import Municipio
from lib.safe_string import EXPEDIENTE_REGEXP

TIPOS_DILIGENCIADOS = [
    (0, "NO DILIGENCIADO"),
    (1, "PARCIALMENTE DILIGENCIADO"),
    (2, "DILIGENCIADO"),
]


class ExhExhortoRespuestaForm(FlaskForm):
    """Formulario para agregar o editar una repuesta al exhorto"""

    exh_exhorto_exhorto_origen_id = StringField("Exhorto Origen ID")  # Read only
    origen_id = StringField("Respuesta Origen ID")  # ReadOnly
    municipio_turnado = SelectField(
        "Municipio turnado", coerce=int, choices=None, validate_choice=False, validators=[DataRequired()]
    )
    area_turnado = SelectField("Área turnado", coerce=int, validators=[DataRequired()])
    numero_exhorto = StringField("Número de Exhorto", validators=[Optional(), Length(max=64), Regexp(EXPEDIENTE_REGEXP)])
    tipo_diligenciado = RadioField("Tipo diligenciado", coerce=int, choices=TIPOS_DILIGENCIADOS, validators=[DataRequired()])
    observaciones = TextAreaField("Observaciones", validators=[Optional()])
    guardar = SubmitField("Guardar")

    def __init__(self, *args, **kwargs):
        """Inicializar y cargar opciones para area_turnado y municipio_turnado"""
        super().__init__(*args, **kwargs)
        self.area_turnado.choices = [(0, "NULO")] + [
            (a.id, a.clave + " - " + a.nombre) for a in ExhArea.query.filter_by(estatus="A").order_by(ExhArea.clave).all()
        ]
        municipios = (
            Municipio.query.join(Estado)
            .filter(Estado.clave == current_app.config["ESTADO_CLAVE"])
            .order_by(Municipio.clave)
            .all()
        )
        self.municipio_turnado.choices = [(0, "NULO")] + [(m.id, m.clave + " - " + m.nombre) for m in municipios]
