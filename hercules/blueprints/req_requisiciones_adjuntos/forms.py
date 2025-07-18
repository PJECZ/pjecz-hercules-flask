"""
Req Requisiciones Adjuntos, formularios
"""

from flask_wtf import FlaskForm
from wtforms import StringField, SubmitField, FileField
from wtforms.validators import DataRequired, Length


class ReqRequisicionAdjuntoForm(FlaskForm):
    """Formulario ReqRequisicionAdjunto"""

    descripcion = StringField("Descripción", validators=[DataRequired(), Length(max=256)])
    archivo = FileField("Archivo", validators=[DataRequired()])
    guardar = SubmitField("Guardar")
