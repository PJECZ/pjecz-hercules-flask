"""
Soportes Tickets, formularios
"""

from flask_wtf import FlaskForm
from wtforms import SelectField, StringField, SubmitField, TextAreaField
from wtforms.validators import DataRequired, Length, Optional

from hercules.blueprints.soportes_categorias.models import SoporteCategoria


class SoporteTicketNewForm(FlaskForm):
    """Formulario para que cualquier usuario pueda crear un ticket"""

    usuario = StringField("Usted es")  # Read only
    oficina = StringField("Se encuentra en")  # Read only
    descripcion = TextAreaField("1. Escriba detalladamente el problema", validators=[DataRequired(), Length(max=4000)])
    guardar = SubmitField("Solicitar soporte")


class SoporteTicketEditForm(FlaskForm):
    """Formulario para Edit"""

    usuario = StringField("Usuario")  # Read only
    descripcion = TextAreaField("Descripción del problema", validators=[DataRequired(), Length(max=4000)])
    categoria = StringField(label="Categoría")  # Read only
    tecnico = StringField(label="Técnico")  # Read only
    departamento = StringField("Departamento")  # Read only
    estado = StringField("Estado")  # Read only
    guardar = SubmitField("Guardar")


class SoporteTicketTakeForm(FlaskForm):
    """Formulario para Take"""

    usuario = StringField("Usuario")  # Read only
    descripcion = TextAreaField("Descripción del problema")  # Read only
    categoria = SelectField("Categoría", coerce=int, validators=[DataRequired()])
    tecnico = StringField("Técnico")  # Read only
    guardar = SubmitField("Tomar")

    def __init__(self, *args, **kwargs):
        """Inicializar y cargar opciones en categoría"""
        super().__init__(*args, **kwargs)
        self.categoria.choices = [
            (c.id, c.nombre) for c in SoporteCategoria.query.filter_by(estatus="A").order_by(SoporteCategoria.nombre).all()
        ]


class SoporteTicketCategorizeForm(FlaskForm):
    """Formulario para Categorize"""

    usuario = StringField("Usuario")  # Read only
    descripcion = TextAreaField("Descripción del problema")  # Read only
    categoria = SelectField("Categoría", coerce=int, validators=[DataRequired()])
    guardar = SubmitField("Categorizar")

    def __init__(self, *args, **kwargs):
        """Inicializar y cargar opciones en categoría"""
        super().__init__(*args, **kwargs)
        self.categoria.choices = [
            (c.id, c.nombre) for c in SoporteCategoria.query.filter_by(estatus="A").order_by(SoporteCategoria.nombre).all()
        ]


class SoporteTicketCloseForm(FlaskForm):
    """Formulario para Close"""

    usuario = StringField("Usuario")  # Read only
    descripcion = TextAreaField("Descripción del problema")  # Read only
    categoria = StringField("Categoría")  # Read only
    tecnico = StringField("Técnico")  # Read only
    soluciones = TextAreaField("Motivo", validators=[DataRequired(), Length(max=1024)])
    guardar = SubmitField("Cerrar")


class SoporteTicketDoneForm(FlaskForm):
    """Formulario para Done"""

    usuario = StringField("Usuario")  # Read only
    descripcion = TextAreaField("Descripción del problema")  # Read only
    categoria = StringField("Categoría")  # Read only
    tecnico = StringField("Técnico")  # Read only
    soluciones = TextAreaField("Solución", validators=[DataRequired(), Length(max=1024)])
    guardar = SubmitField("Terminar")
