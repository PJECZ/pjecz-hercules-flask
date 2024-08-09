"""
Web Paginas, formularios
"""

from flask_wtf import FlaskForm
from wtforms import DateField, SelectField, StringField, SubmitField, TextAreaField
from wtforms.validators import DataRequired, Length, Optional

from hercules.blueprints.web_paginas.models import WebPagina


class WebPaginaForm(FlaskForm):
    """Formulario WebPagina"""

    titulo = StringField("Título", validators=[DataRequired(), Length(max=256)])
    clave = StringField("Clave", validators=[DataRequired(), Length(max=16)])
    fecha_modificacion = DateField("Fecha de modificación", validators=[DataRequired()])
    responsable = StringField("Responsable", validators=[Optional(), Length(max=256)])
    ruta = StringField("Ruta", validators=[DataRequired(), Length(max=256)])
    contenido = TextAreaField("Contenido", validators=[DataRequired()], render_kw={"rows": 10})
    estado = SelectField("Estado", choices=WebPagina.ESTADOS.items(), validators=[DataRequired()])
    guardar = SubmitField("Guardar")
