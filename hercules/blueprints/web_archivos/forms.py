"""
Web Archivos, formularios
"""

from flask_wtf import FlaskForm
from wtforms import StringField, SubmitField
from wtforms.validators import DataRequired, Length


class WebArchivoForm(FlaskForm):
    """Formulario WebArchivo"""

    descripcion = StringField("Descripción", validators=[DataRequired(), Length(max=256)])
    clave = StringField("Clave", validators=[DataRequired(), Length(max=16)])
    archivo = StringField("Archivo", validators=[DataRequired(), Length(max=256)])
    url = StringField("URL", validators=[DataRequired(), Length(max=256)])
    guardar = SubmitField("Guardar")
