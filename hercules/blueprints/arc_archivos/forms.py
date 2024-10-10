"""
Archivo - Archivo, formularios
"""

from flask_wtf import FlaskForm
from wtforms import StringField, SubmitField, DateField
from wtforms.validators import DataRequired, Length, Optional


class ArcEstadisticasDateRangeForm(FlaskForm):
    """Formulario ArcEstadisticasDateRange"""

    fecha_desde = DateField("Desde", validators=[DataRequired()])
    fecha_hasta = DateField("Hasta", validators=[DataRequired()])
    totales = SubmitField("Totales")
    por_distritos = SubmitField("Por Distritos")
    por_instancias = SubmitField("Por Instancias")
    por_archivistas = SubmitField("Por Archivistas")
    por_estados = SubmitField("Por Estados")
