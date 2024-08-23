"""
Inventarios Componentes, formularios
"""

from flask_wtf import FlaskForm
from wtforms import IntegerField, SelectField, StringField, SubmitField
from wtforms.validators import DataRequired, Length, Optional

from hercules.blueprints.inv_categorias.models import InvCategoria
from hercules.blueprints.inv_componentes.models import InvComponente


class InvComponenteForm(FlaskForm):
    """Formulario InvComponente"""

    inv_categoria = SelectField("Categoría", coerce=int, validators=[DataRequired()])
    descripcion = StringField("Descripción", validators=[DataRequired(), Length(max=256)])
    cantidad = IntegerField("Cantidad", validators=[DataRequired()])
    generacion = SelectField("Generación", choices=InvComponente.GENERACIONES.items(), validators=[DataRequired()])
    version = StringField("Versión", validators=[Optional(), Length(max=256)])
    guardar = SubmitField("Guardar")

    def __init__(self, *args, **kwargs):
        """Inicializar y cargar opciones de inv_categoria"""
        super().__init__(*args, **kwargs)
        self.inv_categoria.choices = [
            (c.id, c.nombre) for c in InvCategoria.query.filter_by(estatus="A").order_by(InvCategoria.nombre).all()
        ]
