"""
Exh Exhortos Respuestas, formularios
"""

from flask import current_app
from flask_wtf import FlaskForm
from wtforms import RadioField, SelectField, StringField, SubmitField, TextAreaField
from wtforms.validators import DataRequired, Length, Optional, Regexp

from hercules.blueprints.estados.models import Estado
from hercules.blueprints.exh_areas.models import ExhArea
from hercules.blueprints.exh_exhortos_respuestas.models import ExhExhortoRespuesta
from hercules.blueprints.municipios.models import Municipio
from lib.safe_string import EXPEDIENTE_REGEXP


class ExhExhortoRespuestaForm(FlaskForm):
    """Formulario para agregar o editar una repuesta al exhorto"""

    respuesta_origen_id = StringField("Respuesta Origen ID")  # ReadOnly
    municipio_turnado = SelectField("Municipio turnado", coerce=int, validators=[DataRequired()])
    area_turnado = SelectField("Área turnado", coerce=int, validators=[DataRequired()])
    numero_exhorto = StringField("Número de Exhorto", validators=[Optional(), Length(max=64), Regexp(EXPEDIENTE_REGEXP)])
    tipo_diligenciado = RadioField("Tipo diligenciado", coerce=int, choices=ExhExhortoRespuesta.TIPOS_DILIGENCIADOS.items())
    observaciones = TextAreaField("Observaciones", validators=[Optional()])
    guardar = SubmitField("Guardar")

    def __init__(self, *args, **kwargs):
        """Inicializar y cargar opciones para area_turnado y municipio_turnado"""
        super().__init__(*args, **kwargs)
        exh_areas = ExhArea.query.filter_by(estatus="A").order_by(ExhArea.clave).all()
        self.area_turnado.choices = [(a.id, a.clave + " - " + a.nombre) for a in exh_areas]
        municipios = (
            Municipio.query.join(Estado)
            .filter(Estado.clave == current_app.config["ESTADO_CLAVE"])
            .order_by(Municipio.nombre)
            .all()
        )
        self.municipio_turnado.choices = [(m.id, m.nombre) for m in municipios]
