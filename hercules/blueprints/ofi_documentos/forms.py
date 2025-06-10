"""
Ofi Documentos, formularios
"""

from flask_wtf import FlaskForm
from wtforms import StringField, SubmitField, TextAreaField, IntegerField
from wtforms.validators import DataRequired, Length, Optional


class OfiDocumentoNewForm(FlaskForm):
    """Formulario para crear OfiDocumento"""

    titulo = StringField("Título", validators=[DataRequired(), Length(max=256)])
    contenido = TextAreaField("Contenido", validators=[DataRequired()])
    guardar = SubmitField("Guardar")


class OfiDocumentoEditForm(FlaskForm):
    """Formulario para editar OfiDocumento"""

    titulo = StringField("Título", validators=[DataRequired(), Length(max=256)])
    folio = IntegerField("Folio", validators=[Optional()])
    contenido = TextAreaField("Contenido", validators=[DataRequired()])
    guardar = SubmitField("Guardar")


class OfiDocumentoSignForm(FlaskForm):
    """Formulario para firmar un OfiDocumento"""

    titulo = StringField("Título")  # ReadOnly
    folio = IntegerField("Folio", validators=[DataRequired()])
    firmar = SubmitField("Firmar")
