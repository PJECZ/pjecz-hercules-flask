"""
Funcionario Oficinas, formularios
"""

from flask_wtf import FlaskForm
from wtforms import SelectField, StringField, SubmitField
from wtforms.validators import DataRequired, Length, Optional

from hercules.blueprints.oficinas.models import Oficina


class FuncionarioOficinaForm(FlaskForm):
    """Formulario FuncionarioOficina"""

    funcionario = StringField("Funcionario")  # Read only
    oficina = SelectField("Oficina", coerce=int, validators=[Optional()])  # Select2
    guardar = SubmitField("Guardar")

    print(oficina)

    def __init__(self, *args, **kwargs):
        """Inicializar y cargar opciones de Oficina"""
        super().__init__(*args, **kwargs)
        self.oficina.choices = [(d.id, d.clave) for d in Oficina.query.filter_by(estatus="A").order_by(Oficina.clave).all()]
