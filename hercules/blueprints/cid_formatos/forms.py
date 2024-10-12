"""
CID Formatos, formularios
"""

from flask_wtf import FlaskForm
from flask_wtf.file import FileRequired
from wtforms import FileField, StringField, SubmitField
from wtforms.validators import DataRequired, Length


class CIDFormatoForm(FlaskForm):
    """Formulario CIDFormato"""

    procedimiento_titulo = StringField("Titulo procedimiento")
    codigo = StringField("Clave", validators=[DataRequired(), Length(max=16)])
    descripcion = StringField("Descripción", validators=[DataRequired(), Length(max=256)])
    archivo = FileField("Archivo PDF", validators=[FileRequired()])
    guardar = SubmitField("Guardar")


class CIDFormatoEdit(FlaskForm):
    """Editar Formulario CID Formato"""

    procedimiento_titulo = StringField("Titulo procedimiento")  # Read only
    codigo = StringField("Código", validators=[DataRequired(), Length(max=16)])
    descripcion = StringField("Descripción", validators=[DataRequired(), Length(max=256)])
    guardar = SubmitField("Guardar")
