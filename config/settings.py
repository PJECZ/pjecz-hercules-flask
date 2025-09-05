"""
Settings

Para producción, configure los siguientes secretos en Google Cloud Secret Manager:

- pjecz_hercules_flask_cloud_storage_deposito
- pjecz_hercules_flask_cloud_storage_deposito_edictos
- pjecz_hercules_flask_cloud_storage_deposito_exhortos
- pjecz_hercules_flask_cloud_storage_deposito_glosas
- pjecz_hercules_flask_cloud_storage_deposito_listas_de_acuerdos
- pjecz_hercules_flask_cloud_storage_deposito_oficios
- pjecz_hercules_flask_cloud_storage_deposito_perseo
- pjecz_hercules_flask_cloud_storage_deposito_requisiciones
- pjecz_hercules_flask_cloud_storage_deposito_sentencias
- pjecz_hercules_flask_cloud_storage_deposito_vales_gasolina
- pjecz_hercules_flask_estado_clave
- pjecz_hercules_flask_expediente_virtual_api_key
- pjecz_hercules_flask_expediente_virtual_api_url
- pjecz_hercules_flask_fernet_key
- pjecz_hercules_flask_host
- pjecz_hercules_flask_municipio_clave
- pjecz_hercules_flask_redis_url
- pjecz_hercules_flask_salt
- pjecz_hercules_flask_secret_key
- pjecz_hercules_flask_sqlalchemy_database_uri
- pjecz_hercules_flask_task_queue
- pjecz_hercules_flask_tz
- pjecz_hercules_flask_wtf_csrf_time_limit

Para desarrollo, debe crear un archivo .env con las variables de entorno:

- CLOUD_STORAGE_DEPOSITO
- CLOUD_STORAGE_DEPOSITO_EDICTOS
- CLOUD_STORAGE_DEPOSITO_EXHORTOS
- CLOUD_STORAGE_DEPOSITO_GLOSAS
- CLOUD_STORAGE_DEPOSITO_LISTAS_DE_ACUERDOS
- CLOUD_STORAGE_DEPOSITO_OFICIOS
- CLOUD_STORAGE_DEPOSITO_PERSEO
- CLOUD_STORAGE_DEPOSITO_REQUISICIONES
- CLOUD_STORAGE_DEPOSITO_SENTENCIAS
- CLOUD_STORAGE_DEPOSITO_VALES_GASOLINA
- ESTADO_CLAVE
- EXPEDIENTE_VIRTUAL_API_KEY
- EXPEDIENTE_VIRTUAL_API_URL
- FERNET_KEY
- HOST
- MUNICIPIO_CLAVE
- REDIS_URL
- SALT
- SECRET_KEY
- SQLALCHEMY_DATABASE_URI
- TASK_QUEUE
- TZ
- WTF_CSRF_TIME_LIMIT
"""

import os
from functools import lru_cache

from dotenv import load_dotenv
import google.auth
from google.cloud import secretmanager
from pydantic_settings import BaseSettings

load_dotenv()

MEGABYTE = (2**10) ** 2
PROJECT_ID = os.getenv("PROJECT_ID", "")  # Por defecto está vacío, esto significa estamos en modo local
SERVICE_PREFIX = os.getenv("SERVICE_PREFIX", "pjecz_hercules_flask")


def get_secret(secret_id: str, default: str | None = "") -> str:
    """Get secret from google cloud secret manager"""

    # Si PROJECT_ID está vacío estamos en modo de desarrollo y debe usar las variables de entorno
    if PROJECT_ID == "":
        # Entregar el valor de la variable de entorno, si no esta definida, se entrega el valor por defecto
        value = os.getenv(secret_id.upper(), "")
        if value == "":
            return default
        return value

    # Obtener el project_id con la librería de Google Auth
    _, project_id = google.auth.default()

    # Si NO estamos en Google Cloud, entonces se está ejecutando de forma local
    if not project_id:
        # Entregar el valor de la variable de entorno, si no esta definida, se entrega el valor por defecto
        value = os.getenv(secret_id.upper())
        if value is None:
            return default
        return value

    # Tratar de obtener el secreto
    try:
        # Create the secret manager client
        client = secretmanager.SecretManagerServiceClient()
        # Build the resource name of the secret version
        secret = f"{SERVICE_PREFIX}_{secret_id}"
        name = client.secret_version_path(project_id, secret, "latest")
        # Access the secret version
        response = client.access_secret_version(name=name)
        # Return the decoded payload
        return response.payload.data.decode("UTF-8")
    except:
        pass

    # Entregar el valor por defecto porque no existe el secreto, ni la variable de entorno
    return default


class Settings(BaseSettings):
    """Settings"""

    CLOUD_STORAGE_DEPOSITO: str = get_secret("CLOUD_STORAGE_DEPOSITO")
    CLOUD_STORAGE_DEPOSITO_EDICTOS: str = get_secret("CLOUD_STORAGE_DEPOSITO_EDICTOS")
    CLOUD_STORAGE_DEPOSITO_EXHORTOS: str = get_secret("CLOUD_STORAGE_DEPOSITO_EXHORTOS")
    CLOUD_STORAGE_DEPOSITO_GLOSAS: str = get_secret("CLOUD_STORAGE_DEPOSITO_GLOSAS")
    CLOUD_STORAGE_DEPOSITO_LISTAS_DE_ACUERDOS: str = get_secret("CLOUD_STORAGE_DEPOSITO_LISTAS_DE_ACUERDOS")
    CLOUD_STORAGE_DEPOSITO_OFICIOS: str = get_secret("CLOUD_STORAGE_DEPOSITO_OFICIOS")
    CLOUD_STORAGE_DEPOSITO_PERSEO: str = get_secret("CLOUD_STORAGE_DEPOSITO_PERSEO")
    CLOUD_STORAGE_DEPOSITO_REQUISICIONES: str = get_secret("CLOUD_STORAGE_DEPOSITO_REQUISICIONES")
    CLOUD_STORAGE_DEPOSITO_SENTENCIAS: str = get_secret("CLOUD_STORAGE_DEPOSITO_SENTENCIAS")
    CLOUD_STORAGE_DEPOSITO_VALES_GASOLINA: str = get_secret("CLOUD_STORAGE_DEPOSITO_VALES_GASOLINA")
    ESTADO_CLAVE: str = get_secret("ESTADO_CLAVE", "05")
    EXPEDIENTE_VIRTUAL_API_KEY: str = get_secret("EXPEDIENTE_VIRTUAL_API_KEY")
    EXPEDIENTE_VIRTUAL_API_URL: str = get_secret("EXPEDIENTE_VIRTUAL_API_URL")
    FERNET_KEY: str = get_secret("FERNET_KEY")
    HOST: str = get_secret("HOST")
    MAX_CONTENT_LENGTH: int | None = get_secret("MAX_CONTENT_LENGTH", None)  # Incrementar los formularios
    MAX_FORM_MEMORY_SIZE: int = int(get_secret("MAX_FORM_MEMORY_SIZE", "24")) * MEGABYTE  # Incrementar los formularios
    MUNICIPIO_CLAVE: str = get_secret("MUNICIPIO_CLAVE", "030")
    REDIS_URL: str = get_secret("REDIS_URL", "redis://127.0.0.1:6379")
    SALT: str = get_secret("SALT")
    SECRET_KEY: str = get_secret("SECRET_KEY")
    SQLALCHEMY_DATABASE_URI: str = get_secret("SQLALCHEMY_DATABASE_URI")
    TASK_QUEUE: str = get_secret("TASK_QUEUE", "pjecz_hercules")
    TZ: str = get_secret("TZ", "America/Mexico_City")
    WTF_CSRF_TIME_LIMIT: int = int(get_secret("WTF_CSRF_TIME_LIMIT", "14400"))  # 4 horas por defecto

    class Config:
        """Load configuration"""

        @classmethod
        def customise_sources(cls, init_settings, env_settings, file_secret_settings):
            """Customise sources, first environment variables, then .env file, then google cloud secret manager"""
            return env_settings, file_secret_settings, init_settings


@lru_cache()
def get_settings() -> Settings:
    """Get Settings"""
    return Settings()
