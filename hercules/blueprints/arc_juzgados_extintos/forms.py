"""
Archivo - Juzgados Extintos, formularios
"""

from flask_wtf import FlaskForm
from wtforms import SelectField, StringField, SubmitField
from wtforms.validators import DataRequired, Length, Optional

from hercules.blueprints.distritos.models import Distrito


class ArcJuzgadoExtintoForm(FlaskForm):
    """Formulario ArcJuzgadoExtinto"""

    clave = StringField("Clave", validators=[DataRequired(), Length(max=16)])
    descripcion_corta = StringField("Descripción Corta", validators=[DataRequired(), Length(max=64)])
    descripcion = StringField("Descripción Completa", validators=[DataRequired(), Length(max=256)])
    distrito = SelectField("Distrito", coerce=int, validators=[DataRequired()])
    guardar = SubmitField("Guardar")

    def __init__(self, *args, **kwargs):
        """Inicializar y cargar opciones en distrito"""
        super().__init__(*args, **kwargs)
        self.distrito.choices = [
            (d.id, d.clave + " - " + d.nombre_corto)
            for d in Distrito.query.filter_by(estatus="A").filter_by(es_distrito=True).order_by(Distrito.clave).all()
        ]
