"""
Financieros Vales, formularios
"""

from flask_wtf import FlaskForm
from wtforms import IntegerField, PasswordField, SelectField, StringField, SubmitField, TextAreaField
from wtforms.validators import DataRequired, Length, Optional

from hercules.blueprints.fin_vales.models import FinVale

MONTOS = [
    ("100.0", "$100.00"),
    ("200.0", "$200.00"),
]


class FinValeEditForm(FlaskForm):
    """Formulario para editar un vale"""

    usuario_email = SelectField("Cambiar al usuario con e-mail", coerce=str, validators=[Optional()], validate_choice=False)
    solicito_email = SelectField(
        "Cambiar al solicitante con e-mail", coerce=str, validators=[Optional()], validate_choice=False
    )
    autorizo_email = SelectField(
        "Cambiar al autorizante con e-mail", coerce=str, validators=[Optional()], validate_choice=False
    )
    justificacion = TextAreaField("Justificación", validators=[DataRequired(), Length(max=1024)], render_kw={"rows": 4})
    monto = SelectField("Monto", choices=MONTOS, validators=[DataRequired()])
    actualizar = SubmitField("Actualizar")


class FinValeStep1CreateForm(FlaskForm):
    """Formulario paso 1 crear FinVale"""

    usuario_email = StringField("E-mail del usuario")  # Read only
    solicito_email = StringField("E-mail del solicitante")  # Read only
    autorizo_email = StringField("E-mail del autorizante")  # Read only
    justificacion = TextAreaField("Justificación", validators=[DataRequired(), Length(max=1024)], render_kw={"rows": 4})
    monto = SelectField("Monto", choices=MONTOS, validators=[DataRequired()])
    guardar = SubmitField("Guardar")


class FinValeStep2RequestForm(FlaskForm):
    """Formulario paso 2 solicitar FinVale"""

    contrasena = PasswordField("Contraseña de su firma electrónica", validators=[DataRequired(), Length(6, 64)])
    solicitar = SubmitField("Solicitar")


class FinValeCancel2RequestForm(FlaskForm):
    """Formulario cancelar solicitado FinVale"""

    motivo = StringField("Motivo", validators=[DataRequired(), Length(max=256)])
    contrasena = PasswordField("Contraseña de su firma electrónica", validators=[DataRequired(), Length(6, 64)])
    cancelar = SubmitField("Cancelar")


class FinValeStep3AuthorizeForm(FlaskForm):
    """Formulario paso 3 autorizar FinVale"""

    contrasena = PasswordField("Contraseña de su firma electrónica", validators=[DataRequired(), Length(6, 64)])
    autorizar = SubmitField("Autorizar")


class FinValeCancel3AuthorizeForm(FlaskForm):
    """Formulario cancelar autorizado FinVale"""

    motivo = StringField("Motivo", validators=[DataRequired(), Length(max=256)])
    contrasena = PasswordField("Contraseña de su firma electrónica", validators=[DataRequired(), Length(6, 64)])
    cancelar = SubmitField("Cancelar")


class FinValeStep4DeliverForm(FlaskForm):
    """Formulario paso 4 entregar FinVale"""

    folio = IntegerField("Folio", validators=[DataRequired()])
    entregar = SubmitField("Entregar")


class FinValeStep5AttachmentsForm(FlaskForm):
    """Formulario paso 5 adjuntar FinVale"""

    vehiculo_descripcion = StringField("Descripción del vehículo", validators=[DataRequired(), Length(max=256)])
    tanque_inicial = StringField("Tanque inicial", validators=[Optional(), Length(max=48)])
    tanque_final = StringField("Tanque final", validators=[Optional(), Length(max=48)])
    kilometraje_inicial = IntegerField("Kilometraje inicial", validators=[Optional()])
    kilometraje_final = IntegerField("Kilometraje final", validators=[Optional()])
    concluir = SubmitField("Concluir entrega de adjuntos")


class FinValeStep6ArchiveForm(FlaskForm):
    """Formulario paso 6 archivar FinVale"""

    notas = TextAreaField("Notas", validators=[DataRequired(), Length(max=1020)])
    archivar = SubmitField("Archivar")
