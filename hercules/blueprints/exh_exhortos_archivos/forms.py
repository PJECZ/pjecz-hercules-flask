"""
Exh Exhortos Archivos, formularios
"""

from flask_wtf import FlaskForm
from flask_wtf.file import FileField, FileRequired
from wtforms import SelectField, StringField, SubmitField
from wtforms.validators import DataRequired, Length

from hercules.blueprints.exh_exhortos_archivos.models import ExhExhortoArchivo


class ExhExhortoArchivoNewForm(FlaskForm):
    """Formulario para subir un archivo"""

    tipo_documento = SelectField(
        "Tipo", coerce=int, choices=ExhExhortoArchivo.TIPOS_DOCUMENTOS.items(), validators=[DataRequired()]
    )
    archivo = FileField("Archivo PDF", validators=[FileRequired()])
    subir = SubmitField("Subir")


class ExhExhortoArchivoEditForm(FlaskForm):
    """Formulario para editar un archivo"""

    nombre_archivo = StringField("Nombre del Archivo")  # Read only
    tipo_documento = SelectField(
        "Tipo", coerce=int, choices=ExhExhortoArchivo.TIPOS_DOCUMENTOS.items(), validators=[DataRequired()]
    )
    hash_sha1 = StringField("Hash SHA-1")  # Read only
    hash_sha256 = StringField("Hash SHA-256")  # Read only
    url = StringField("URL")  # Read only
    tamano = StringField("Tamaño")  # Read only
    fecha_hora_recepcion = StringField("Fecha y hora de recepción")  # Read only
    guardar = SubmitField("Guardar")
