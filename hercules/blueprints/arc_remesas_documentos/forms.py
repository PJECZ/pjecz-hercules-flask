"""
Archivo - Remesas Documentos, formularios
"""

from flask_wtf import FlaskForm
from wtforms import StringField, SubmitField, IntegerField, SelectField, TextAreaField
from wtforms.validators import DataRequired, Length, Optional

from hercules.blueprints.arc_remesas_documentos.models import ArcRemesaDocumento


def anomalias_tipos():
    anomalias = ArcRemesaDocumento.ANOMALIAS
    # anomalias.update({"": ""})
    # anomalias.move_to_end("", last=False)
    anomalias[""] = ""
    return anomalias.items()


class ArcRemesaDocumentoEditForm(FlaskForm):
    """Formulario para editar Documento anexo en Remesa"""

    fojas = IntegerField("Fojas", validators=[DataRequired()])
    tipo_juzgado = SelectField("Tipo de Instancia", choices=ArcRemesaDocumento.TIPOS.items(), validators=[DataRequired()])
    observaciones_solicitante = TextAreaField("Observaciones", validators=[Optional(), Length(max=256)])
    guardar = SubmitField("Guardar")


class ArcRemesaDocumentoArchiveForm(FlaskForm):
    """Formulario para archivar Documento anexo en Remesa"""

    fojas = IntegerField("Fojas", validators=[Optional()])
    anomalia = SelectField("Anomalía", validators=[Optional()], choices=anomalias_tipos())
    observaciones_archivista = TextAreaField("Observaciones", validators=[Optional(), Length(max=256)])
    archivar = SubmitField("Archivar")
