"""
Web Paginas, formularios
"""

from flask_wtf import FlaskForm
from wtforms import DateField, DateTimeLocalField, StringField, SubmitField, TextAreaField
from wtforms.validators import DataRequired, Length, Optional


class WebPaginaNewForm(FlaskForm):
    """Formulario WebPagina"""

    clave = StringField("Clave", validators=[DataRequired(), Length(max=16)])
    titulo = StringField("Título", validators=[DataRequired(), Length(max=256)])
    ruta = StringField("Ruta", validators=[DataRequired(), Length(max=256)])
    guardar = SubmitField("Guardar")


class WebPaginaEditForm(FlaskForm):
    """Formulario WebPagina"""

    clave = StringField("Clave", validators=[DataRequired(), Length(max=16)])
    titulo = StringField("Título", validators=[DataRequired(), Length(max=256)])
    resumen = TextAreaField("Resumen", validators=[Optional()], render_kw={"rows": 8})
    ruta = StringField("Ruta", validators=[DataRequired(), Length(max=256)])
    fecha_modificacion = DateField("Fecha de modificación", validators=[DataRequired()])
    responsable = StringField("Responsable", validators=[Optional(), Length(max=256)])
    etiquetas = StringField("Etiquetas", validators=[Optional(), Length(max=256)])
    vista_previa = StringField("Vista previa", validators=[Optional(), Length(max=256)])
    tiempo_publicar = DateTimeLocalField("Cuándo publicar", validators=[Optional()])
    tiempo_archivar = DateTimeLocalField("Cuándo archivar", validators=[Optional()])
    guardar = SubmitField("Guardar")


class WebPaginaContenidoForm(FlaskForm):
    """Formulario Contenido WebPagina"""

    contenido = TextAreaField("Contenido", validators=[DataRequired()], render_kw={"rows": 10})
    guardar = SubmitField("Guardar")
