"""
DGT Rutas, formularios
"""

from flask_wtf import FlaskForm
from wtforms import SelectField, StringField, SubmitField
from wtforms.validators import DataRequired, Length

from hercules.blueprints.dgt_depositos.models import DgtDepositos
from hercules.blueprints.dgt_tipos.models import DgtTipo


class DgtRutaForm(FlaskForm):
    """Formulario DgtRuta"""

    dgt_deposito = SelectField("Depósito", coerce=str, validators=[DataRequired()])
    autoridad_clave = StringField("Autoridad Clave", validators=[DataRequired(), Length(max=16)])
    dgt_tipo = SelectField("Tipo", coerce=str, validators=[DataRequired()])
    clave = StringField("Clave (depósito-autoridad_clave-exp|exh)", validators=[DataRequired(), Length(max=64)])
    directorio = StringField("Directorio (sin diagonales al inicio o final)", validators=[DataRequired(), Length(max=512)])
    guardar = SubmitField("Guardar")

    def __init__(self, *args, **kwargs):
        """Inicializar y cargar opciones en dgt_deposito y dgt_tipo"""
        super().__init__(*args, **kwargs)
        self.dgt_deposito.choices = [
            (str(d.id), f"{d.clave} ({d.descripcion})")
            for d in DgtDepositos.query.filter_by(estatus="A").order_by(DgtDepositos.clave).all()
        ]
        self.dgt_tipo.choices = [
            (str(t.id), f"{t.clave} ({t.descripcion})")
            for t in DgtTipo.query.filter_by(estatus="A").order_by(DgtTipo.clave).all()
        ]
