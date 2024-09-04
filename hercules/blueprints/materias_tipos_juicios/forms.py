"""
Materias-Tipos de Juicios, formularios
"""

from flask_wtf import FlaskForm
from wtforms import SelectField, StringField, SubmitField
from wtforms.validators import DataRequired, Length

from hercules.blueprints.materias.models import Materia


class MateriaTipoJuicioForm(FlaskForm):
    """Formulario MateriaTipoJuicio"""

    materia = SelectField("Materia", coerce=int, validators=[DataRequired()])
    descripcion = StringField("Descripción", validators=[DataRequired(), Length(max=256)])
    guardar = SubmitField("Guardar")

    def __init__(self, *args, **kwargs):
        """Inicializar y cargar opciones en distrito"""
        super().__init__(*args, **kwargs)
        self.materia.choices = [(d.id, d.nombre) for d in Materia.query.filter_by(estatus="A").order_by(Materia.nombre).all()]
