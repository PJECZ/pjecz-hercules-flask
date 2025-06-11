"""
Ofi Plantillas, formularios
"""

from flask_wtf import FlaskForm
from wtforms import StringField, SubmitField, TextAreaField, BooleanField
from wtforms.validators import DataRequired, Length, Optional


class OfiPlantillaForm(FlaskForm):
    """Formulario OfiPlantilla"""

    titulo = StringField("Título", validators=[DataRequired()])
    contenido_sfdt = TextAreaField("Contenido SFDT", validators=[Optional()], render_kw={"rows": 10})
    esta_archivado = BooleanField("Activo", validators=[Optional()])
    guardar = SubmitField("Guardar")
