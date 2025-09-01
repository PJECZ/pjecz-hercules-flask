"""
Req Catalogo, formularios
"""

from flask_wtf import FlaskForm
from wtforms import StringField, SubmitField, SelectField
from wtforms.validators import DataRequired, Length, Optional

from hercules.blueprints.req_catalogos.models import ReqCatalogo
from hercules.blueprints.req_categorias.models import ReqCategoria


class ReqCatalogoForm(FlaskForm):
    """Formulario ReqCatalogo"""

    codigo = StringField("Código", validators=[DataRequired(), Length(max=16)])
    descripcion = StringField("Descripción", validators=[DataRequired(), Length(max=256)])
    categoria = SelectField("Categoría", coerce=int, validators=[DataRequired()])
    unidad_medida = SelectField("Unidad de medida", choices=ReqCatalogo.UNIDADES_MEDIDAS.items(), validators=[DataRequired()])
    guardar = SubmitField("Guardar")

    def __init__(self, *args, **kwargs):
        """Inicializar y cargar opciones en categoria"""
        super().__init__(*args, **kwargs)
        self.categoria.choices = [
            (c.id, c.clave_descripcion) for c in ReqCategoria.query.filter_by(estatus="A").order_by(ReqCategoria.clave).all()
        ]


class ReqCatalogoWithCategoriaForm(FlaskForm):
    """Formulario ReqCatalogo con Categoría seleccionada"""

    codigo = StringField("Código", validators=[DataRequired(), Length(max=16)])
    descripcion = StringField("Descripción", validators=[DataRequired(), Length(max=256)])
    categoria = StringField("Categoría")  # Read Only
    unidad_medida = SelectField("Unidad de medida", choices=ReqCatalogo.UNIDADES_MEDIDAS.items(), validators=[DataRequired()])
    guardar = SubmitField("Guardar")
