"""
Peritos, formularios
"""

from flask_wtf import FlaskForm
from wtforms import DateField, SelectField, StringField, SubmitField
from wtforms.validators import DataRequired, Email, Length, Optional

from hercules.blueprints.distritos.models import Distrito
from hercules.blueprints.peritos_tipos.models import PeritoTipo


class PeritoForm(FlaskForm):
    """Formulario Perito"""

    nombre = StringField("Nombre", validators=[DataRequired(), Length(max=256)])
    distrito = SelectField("Distrito", coerce=int, validators=[DataRequired()])
    perito_tipo = SelectField("Tipos de Perito", coerce=int, validators=[DataRequired()])
    domicilio = StringField("Domicilio", validators=[Optional(), Length(max=256)])
    telefono_fijo = StringField("Teléfono fijo", validators=[Optional(), Length(max=256)])
    telefono_celular = StringField("Teléfono celular", validators=[Optional(), Length(max=256)])
    email = StringField("e-mail", validators=[Optional(), Email()])
    notas = StringField("Notas", validators=[Optional()])
    renovacion = DateField("Renovación", validators=[DataRequired()])
    guardar = SubmitField("Guardar")

    def __init__(self, *args, **kwargs):
        """Inicializar y cargar opciones en distrito y perito_tipo"""
        super().__init__(*args, **kwargs)
        self.distrito.choices = [
            (d.id, d.nombre_corto)
            for d in Distrito.query.filter_by(es_distrito=True, estatus="A").order_by(Distrito.nombre_corto).all()
        ]
        self.perito_tipo.choices = [
            (p.id, p.nombre) for p in PeritoTipo.query.filter_by(estatus="A").order_by(PeritoTipo.nombre).all()
        ]
