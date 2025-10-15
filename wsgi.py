"""
PJECZ Hercules Flask

Ejecutar con Gunicorn como servidor WSGI en contenedores

    gunicorn --bind :5000 --workers 4 wsgi:app

"""

from hercules.app import create_app

app = create_app()

if __name__ == "__main__":
    app.run()
