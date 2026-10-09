"""
DGT Plataformas Endpoints, formularios
"""

import json

from flask_wtf import FlaskForm
from wtforms import SelectField, StringField, SubmitField, TextAreaField
from wtforms.validators import DataRequired, Length, Optional, ValidationError

from hercules.blueprints.dgt_plataformas.models import DgtPlataforma
from hercules.blueprints.dgt_plataformas_endpoints.models import DgtPlataformaEndpoint


class DgtPlataformaEndpointForm(FlaskForm):
    """Formulario DgtPlataformaEndpoint"""

    dgt_plataforma = SelectField("Plataforma", coerce=str, validators=[DataRequired()])
    descripcion = StringField("Descripción", validators=[DataRequired(), Length(max=256)])
    ruta = StringField("Ruta", validators=[DataRequired(), Length(max=512)])
    proposito = SelectField("Propósito", choices=DgtPlataformaEndpoint.PROPOSITOS.items(), validators=[DataRequired()])
    metodo = SelectField("Método", choices=DgtPlataformaEndpoint.METODOS.items(), validators=[DataRequired()])
    payload_muestra = TextAreaField("Muestra del payload (JSON)", validators=[Optional()], render_kw={"rows": 10})
    guardar = SubmitField("Guardar")

    def __init__(self, *args, **kwargs):
        """Inicializar y cargar opciones en dgt_plataforma"""
        super().__init__(*args, **kwargs)
        self.dgt_plataforma.choices = [
            (str(p.id), p.descripcion)
            for p in DgtPlataforma.query.filter_by(estatus="A").order_by(DgtPlataforma.descripcion).all()
        ]

    def validate_payload_muestra(self, field):
        """Validar que la muestra del payload sea un JSON válido"""
        if (field.data or "").strip() != "":
            try:
                json.loads(field.data)
            except json.JSONDecodeError as error:
                raise ValidationError(f"No es un JSON válido: {error}") from error
