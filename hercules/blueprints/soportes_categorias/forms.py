"""
Soportes Categorías, formularios
"""

from flask_wtf import FlaskForm
from wtforms import SelectField, StringField, SubmitField, TextAreaField
from wtforms.validators import DataRequired, Length, Optional

from hercules.blueprints.roles.models import Rol
from hercules.blueprints.soportes_categorias.models import SoporteCategoria


class SoporteCategoriaForm(FlaskForm):
    """Formulario SoporteCategoria"""

    nombre = StringField("Nombre", validators=[DataRequired(), Length(max=256)])
    rol = SelectField("Rol", coerce=int, validators=[Optional()])
    instrucciones = TextAreaField("Instrucciones", validators=[Optional(), Length(max=4096)])
    departamento = SelectField("Departamento", choices=SoporteCategoria.DEPARTAMENTOS.items(), validators=[DataRequired()])
    guardar = SubmitField("Guardar")

    def __init__(self, *args, **kwargs):
        """Inicializar y cargar opciones en rol"""
        super().__init__(*args, **kwargs)
        self.rol.choices = [(r.id, r.nombre) for r in Rol.query.filter_by(estatus="A").order_by(Rol.nombre).all()]
