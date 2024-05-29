"""
Autoridades, formularios
"""

from flask import current_app
from flask_wtf import FlaskForm
from wtforms import BooleanField, SelectField, StringField, SubmitField
from wtforms.validators import DataRequired, Length, Optional, Regexp

from lib.safe_string import CLAVE_REGEXP
from hercules.blueprints.distritos.models import Distrito
from hercules.blueprints.estados.models import Estado
from hercules.blueprints.municipios.models import Municipio


class AutoridadForm(FlaskForm):
    """Formulario Autoridad"""

    distrito = SelectField("Distrito", coerce=int, validators=[DataRequired()])
    municipio = SelectField("Municipio", coerce=int, validators=[DataRequired()])
    clave = StringField("Clave (hasta 16 caracteres)", validators=[DataRequired(), Regexp(CLAVE_REGEXP)])
    descripcion = StringField("Descripción", validators=[DataRequired(), Length(max=256)])
    descripcion_corta = StringField("Descripción corta (máximo 64 caracteres)", validators=[DataRequired(), Length(max=64)])
    es_archivo_solicitante = BooleanField("Es Archivo Solicitante", validators=[Optional()])
    es_cemasc = BooleanField("Es CEMASC", validators=[Optional()])
    es_defensoria = BooleanField("Es Defensoría", validators=[Optional()])
    es_extinto = BooleanField("Es Extinto", validators=[Optional()])
    es_jurisdiccional = BooleanField("Es Jurisdiccional", validators=[Optional()])
    es_notaria = BooleanField("Es Notaría", validators=[Optional()])
    es_organo_especializado = BooleanField("Es Órgano Especializado", validators=[Optional()])
    es_revisor_escrituras = BooleanField("Es revisor de escrituras", validators=[Optional()])
    guardar = SubmitField("Guardar")

    def __init__(self, *args, **kwargs):
        """Inicializar y cargar opciones de distritos"""
        super().__init__(*args, **kwargs)
        self.distrito.choices = [
            (d.id, d.clave + " - " + d.nombre_corto)
            for d in Distrito.query.filter_by(estatus="A").order_by(Distrito.clave).all()
        ]
        self.municipio.choices = [
            (m.id, m.clave + " - " + m.nombre)
            for m in Municipio.query.join(Estado)
            .filter(Estado.clave == current_app.config["ESTADO_CLAVE"])
            .order_by(Municipio.clave)
            .all()
        ]
