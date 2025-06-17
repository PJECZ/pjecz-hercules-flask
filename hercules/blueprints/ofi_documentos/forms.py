"""
Ofi Documentos, formularios
"""

from flask_wtf import FlaskForm
from wtforms import StringField, SubmitField, TextAreaField, DateField
from wtforms.validators import DataRequired, Length, Optional, Regexp

FOLIO_REGEXP = r"^(\w.[-\/])*\d+\/\d{4}$"


class OfiDocumentoNewForm(FlaskForm):
    """Formulario para crear OfiDocumento"""

    descripcion = StringField("Descripción", validators=[DataRequired(), Length(max=256)])
    folio = StringField("Folio", validators=[Optional(), Regexp(FOLIO_REGEXP)])
    vencimiento_fecha = DateField("Fecha de Vencimiento", validators=[Optional()])
    contenido_sfdt = TextAreaField("Contenido SFDT", validators=[Optional()], render_kw={"rows": 10})
    guardar = SubmitField("Guardar")


class OfiDocumentoEditForm(FlaskForm):
    """Formulario para editar OfiDocumento"""

    descripcion = StringField("Descripción", validators=[DataRequired(), Length(max=256)])
    folio = StringField("Folio", validators=[Optional(), Regexp(FOLIO_REGEXP)])
    vencimiento_fecha = DateField("Fecha de Vencimiento", validators=[Optional()])
    contenido_sfdt = TextAreaField("Contenido SFDT", validators=[Optional()], render_kw={"rows": 10})
    guardar = SubmitField("Guardar")


class OfiDocumentoSignForm(FlaskForm):
    """Formulario para firmar un OfiDocumento"""

    descripcion = StringField("Descripción", validators=[DataRequired(), Length(max=256)])
    folio = StringField("Folio", validators=[DataRequired(), Regexp(FOLIO_REGEXP)])
    contenido_sfdt = TextAreaField("Contenido SFDT", validators=[Optional()], render_kw={"rows": 10})  # Read Only
    firmar = SubmitField("Firmar")
