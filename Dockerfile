# Use an official Python runtime as a parent image
FROM python:3.11-slim

# Set environment variables for Python
ENV PYTHONUNBUFFERED=1
ENV PYTHONDONTWRITEBYTECODE=1

# Create and change to the app directory
WORKDIR /usr/src/app

# Install system dependencies and locales
RUN apt-get update \
    && apt-get install -y --no-install-recommends build-essential \
    && apt-get install -y locales \
    && rm -rf /var/lib/apt/lists/*

# Configurate locale es_MX.UTF-8
RUN sed -i '/es_MX.UTF-8/s/^# //g' /etc/locale.gen \
    && locale-gen
ENV LANG es_MX.UTF-8
ENV LANGUAGE es_MX:es
ENV LC_ALL es_MX.UTF-8

# Copy requirements file
COPY requirements.txt ./

# Install Python dependencies
RUN pip install --upgrade pip && pip install -r requirements.txt

# Copy application code
COPY . ./

# Run the web service on container startup
# Set desired Gunicorn worker count (adjust based on Cloud Run CPU/Memory and expected load)
# Cloud Run v2 usually provides at least 1 CPU, v1 might share, start with 1 or 2
# Timeout is set to 0 to disable the timeouts of the workers to allow Cloud Run to handle instance scaling
CMD exec gunicorn --bind :$PORT --workers 1 --threads 8 --timeout 0 wsgi:app
