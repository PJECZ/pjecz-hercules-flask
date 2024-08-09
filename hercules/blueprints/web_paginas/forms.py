"""
Web Paginas, formularios
"""

from flask_wtf import FlaskForm
from wtforms import DateField, StringField, SubmitField, TextAreaField
from wtforms.validators import DataRequired, Length, Optional


class WebPaginaForm(FlaskForm):
    """Formulario WebPagina"""

    web_rama_clave = StringField("Rama clave")  # Solo lectura
    web_rama_nombre = StringField("Rama nombre")  # Solo lectura
    titulo = StringField("Título", validators=[DataRequired(), Length(max=256)])
    fecha_modificacion = DateField("Fecha de modificación", validators=[DataRequired()])
    responsable = StringField("Responsable", validators=[Optional(), Length(max=256)])
    ruta = StringField("Ruta", validators=[DataRequired(), Length(max=256)])
    contenido = TextAreaField("Contenido", validators=[DataRequired()])
    guardar = SubmitField("Guardar")
