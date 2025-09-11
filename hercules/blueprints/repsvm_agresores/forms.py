"""
REPSVM Agresores, formularios
"""

from flask_wtf import FlaskForm
from wtforms import IntegerField, SelectField, StringField, SubmitField, TextAreaField
from wtforms.validators import DataRequired, Length, Optional, Regexp, NumberRange

from hercules.blueprints.distritos.models import Distrito
from hercules.blueprints.repsvm_agresores.models import REPSVMAgresor
from lib.safe_string import URL_REGEXP


class REPSVMAgresorForm(FlaskForm):
    """Formulario REPSVMAgresor"""

    consecutivo = IntegerField("Consecutivo", validators=[DataRequired(), NumberRange(min=0, max=99999)])
    distrito = SelectField("Distrito", coerce=int, validators=[DataRequired()])
    delito_generico = StringField("Delito genérico", validators=[DataRequired(), Length(max=256)])
    delito_especifico = TextAreaField("Delito específico", validators=[DataRequired(), Length(max=1024)])
    nombre = StringField("Nombre", validators=[DataRequired(), Length(max=256)])
    numero_causa = StringField("Numero de causa", validators=[DataRequired(), Length(max=256)])
    pena_impuesta = StringField("Pena impuesta", validators=[DataRequired(), Length(max=256)])
    tipo_juzgado = SelectField("Tipo de juzgado", choices=REPSVMAgresor.TIPOS_JUZGADOS.items(), validators=[DataRequired()])
    tipo_sentencia = SelectField(
        "Tipo de sentencia", choices=REPSVMAgresor.TIPOS_SENTENCIAS.items(), validators=[DataRequired()]
    )
    sentencia_url = StringField("V.P. Sentencia URL", validators=[Optional(), Length(max=512), Regexp(URL_REGEXP)])
    observaciones = TextAreaField("Observaciones", validators=[Optional(), Length(max=4092)])
    guardar = SubmitField("Guardar")

    def __init__(self, *args, **kwargs):
        """Inicializar y cargar opciones en distrito"""
        super().__init__(*args, **kwargs)
        self.distrito.choices = [
            (d.id, d.nombre)
            for d in Distrito.query.filter_by(es_distrito_judicial=True, estatus="A").order_by(Distrito.nombre).all()
        ]
