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
    municipio_turnado = SelectField("Municipio turnado", coerce=str, validators=[DataRequired()])
    area_turnado = SelectField("Área turnado", coerce=str, validators=[DataRequired()])
    numero_exhorto = StringField("Número de Exhorto", validators=[Optional(), Length(max=64), Regexp(EXPEDIENTE_REGEXP)])
    tipo_diligenciado = RadioField("Tipo diligenciado", coerce=int, choices=ExhExhortoRespuesta.TIPOS_DILIGENCIADOS.items())
    observaciones = TextAreaField("Observaciones", validators=[Optional(), Length(max=1024)], render_kw={"rows": 5})
    guardar = SubmitField("Guardar")

    def __init__(self, *args, **kwargs):
        """Inicializar y cargar opciones para area_turnado y municipio_turnado"""
        super().__init__(*args, **kwargs)
        # Cargar la opciones para area_turnado como (clave, nombre)
        exh_areas = ExhArea.query.filter_by(estatus="A").order_by(ExhArea.clave).all()
        self.area_turnado.choices = [(a.clave, a.clave + " - " + a.nombre) for a in exh_areas]
        # Cargar las opciones para municipio_turnado como (clave, nombre)
        municipios = (
            Municipio.query.join(Estado)
            .filter(Estado.clave == current_app.config["ESTADO_CLAVE"])
            .order_by(Municipio.nombre)
            .all()
        )
        self.municipio_turnado.choices = [(m.clave, m.nombre) for m in municipios]
