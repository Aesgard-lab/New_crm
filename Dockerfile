# ==============================================
# DOCKERFILE MULTI-STAGE PARA CRM DJANGO
# ==============================================
# Optimizado para producción con:
# - Multi-stage build para imagen más pequeña
# - Usuario no-root por seguridad
# - Cache de dependencias
# - Health checks

# ----------------------------------------------
# STAGE 1: Builder - Instalar dependencias
# ----------------------------------------------
FROM python:3.12-slim as builder

# Evitar escritura de .pyc y buffering
ENV PYTHONDONTWRITEBYTECODE=1
ENV PYTHONUNBUFFERED=1

WORKDIR /app

# Instalar dependencias del sistema necesarias para compilar
RUN apt-get update && apt-get install -y --no-install-recommends \
    build-essential \
    libpq-dev \
    && rm -rf /var/lib/apt/lists/*

# Copiar requirements primero para aprovechar cache de Docker
COPY requirements.txt .

# Crear virtualenv e instalar dependencias
RUN python -m venv /opt/venv
ENV PATH="/opt/venv/bin:$PATH"

RUN pip install --upgrade pip && \
    pip install --no-cache-dir -r requirements.txt

# ----------------------------------------------
# STAGE 2: Runtime - Imagen final
# ----------------------------------------------
FROM python:3.12-slim as runtime

# Variables de entorno
ENV PYTHONDONTWRITEBYTECODE=1
ENV PYTHONUNBUFFERED=1
ENV PATH="/opt/venv/bin:$PATH"
ENV APP_HOME=/app

WORKDIR $APP_HOME

# Instalar solo dependencias de runtime
RUN apt-get update && apt-get install -y --no-install-recommends \
    libpq5 \
    curl \
    && rm -rf /var/lib/apt/lists/* \
    && apt-get clean

# Copiar virtualenv desde builder
COPY --from=builder /opt/venv /opt/venv

# Crear usuario no-root para seguridad
RUN groupadd --gid 1000 appgroup && \
    useradd --uid 1000 --gid appgroup --shell /bin/bash --create-home appuser

# Crear directorios necesarios
RUN mkdir -p $APP_HOME/staticfiles \
             $APP_HOME/media \
             $APP_HOME/logs && \
    chown -R appuser:appgroup $APP_HOME

# Copiar código de la aplicación
COPY --chown=appuser:appgroup . $APP_HOME

# Cambiar a usuario no-root
USER appuser

# Exponer puerto
EXPOSE 8000

# Health check usando el nuevo endpoint de liveness
HEALTHCHECK --interval=30s --timeout=10s --start-period=10s --retries=3 \
    CMD curl -f http://localhost:8000/health/live/ || exit 1

# Script de entrada
COPY --chown=appuser:appgroup docker/entrypoint.sh /entrypoint.sh
RUN chmod +x /entrypoint.sh

ENTRYPOINT ["/entrypoint.sh"]

# Comando por defecto: Gunicorn
CMD ["gunicorn", "config.wsgi:application", "--bind", "0.0.0.0:8000", "--workers", "3"]
