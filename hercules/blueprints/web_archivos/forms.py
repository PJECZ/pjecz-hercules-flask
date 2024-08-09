"""
Web Archivos, formularios
"""

from flask_wtf import FlaskForm
from wtforms import StringField, SubmitField
from wtforms.validators import DataRequired, Length, Optional


class WebArchivoForm(FlaskForm):
    """Formulario WebArchivo"""

    web_pagina_titulo = StringField("Título")  # Solo lectura
    archivo = StringField("Archivo", validators=[DataRequired(), Length(max=256)])
    descripcion = StringField("Descripción", validators=[Optional(), Length(max=256)])
    url = StringField("URL", validators=[DataRequired(), Length(max=256)])
    guardar = SubmitField("Guardar")
