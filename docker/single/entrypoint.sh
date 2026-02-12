#!/bin/bash
# ==============================================
# ENTRYPOINT - Contenedor único all-in-one
# ==============================================
set -e

echo "=========================================="
echo "  CRM Django - Contenedor Único"
echo "  Nginx + Redis + Gunicorn + Celery"
echo "=========================================="

# Defaults
export GUNICORN_WORKERS=${GUNICORN_WORKERS:-2}
export CELERY_CONCURRENCY=${CELERY_CONCURRENCY:-1}

# ----------------------------------------------
# Esperar a PostgreSQL
# ----------------------------------------------
echo "[1/4] Esperando base de datos..."
PGHOST=${POSTGRES_HOST:-db}
PGPORT=${POSTGRES_PORT:-5432}

for i in $(seq 1 30); do
    if nc -z "$PGHOST" "$PGPORT" 2>/dev/null; then
        echo "  ✓ PostgreSQL disponible"
        break
    fi
    echo "  - Esperando PostgreSQL ($i/30)..."
    sleep 2
done

# ----------------------------------------------
# Migraciones y collectstatic
# ----------------------------------------------
echo "[2/4] Ejecutando migraciones..."
cd /app
python manage.py migrate --noinput 2>&1 | tail -5

echo "[3/4] Recopilando archivos estáticos..."
python manage.py collectstatic --noinput --clear 2>&1 | tail -3

# ----------------------------------------------
# Ajustar permisos
# ----------------------------------------------
echo "[4/4] Preparando directorios..."
chown -R appuser:appgroup /app/staticfiles /app/media /app/logs 2>/dev/null || true
chown -R appuser:appgroup /var/lib/redis /var/log/supervisor 2>/dev/null || true

echo "=========================================="
echo "  ✓ Listo - Workers: $GUNICORN_WORKERS | Celery: $CELERY_CONCURRENCY"
echo "=========================================="

# Ejecutar comando (supervisord)
exec "$@"
