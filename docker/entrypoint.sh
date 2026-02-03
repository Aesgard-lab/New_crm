#!/bin/bash
# ==============================================
# ENTRYPOINT SCRIPT PARA DJANGO
# ==============================================
# Este script se ejecuta al iniciar el contenedor
# Prepara el entorno antes de ejecutar el comando principal

set -e

echo "=========================================="
echo "  CRM Django - Iniciando contenedor"
echo "=========================================="

# ----------------------------------------------
# Esperar a que la base de datos este lista
# ----------------------------------------------
echo "[1/5] Esperando base de datos..."

if [ -n "$POSTGRES_HOST" ]; then
    while ! nc -z "$POSTGRES_HOST" "${POSTGRES_PORT:-5432}"; do
        echo "  - PostgreSQL no disponible, reintentando en 2s..."
        sleep 2
    done
    echo "  - PostgreSQL disponible!"
fi

# ----------------------------------------------
# Esperar a que Redis este listo
# ----------------------------------------------
echo "[2/5] Esperando Redis..."

if [ -n "$REDIS_URL" ]; then
    # Extraer host y puerto de REDIS_URL
    REDIS_HOST=$(echo "$REDIS_URL" | sed -e 's|redis://||' -e 's|:.*||' -e 's|@||g' | cut -d'/' -f1 | cut -d'@' -f2)
    REDIS_HOST=${REDIS_HOST:-redis}
    
    while ! nc -z "$REDIS_HOST" 6379; do
        echo "  - Redis no disponible, reintentando en 2s..."
        sleep 2
    done
    echo "  - Redis disponible!"
fi

# ----------------------------------------------
# Ejecutar migraciones (solo si es web principal)
# ----------------------------------------------
echo "[3/5] Verificando migraciones..."

# Solo ejecutar migraciones si el comando es gunicorn o runserver
if [[ "$1" == "gunicorn" ]] || [[ "$1" == "python" && "$2" == "manage.py" && "$3" == "runserver" ]]; then
    echo "  - Aplicando migraciones pendientes..."
    python manage.py migrate --noinput
    echo "  - Migraciones completadas!"
else
    echo "  - Saltando migraciones (no es servidor web)"
fi

# ----------------------------------------------
# Recolectar archivos estaticos (solo produccion)
# ----------------------------------------------
echo "[4/5] Verificando archivos estaticos..."

if [ "$DJANGO_ENV" = "production" ] || [ "$DJANGO_ENV" = "staging" ]; then
    if [[ "$1" == "gunicorn" ]]; then
        echo "  - Recolectando archivos estaticos..."
        python manage.py collectstatic --noinput --clear
        
        # Verificar que se crearon los archivos
        STATIC_COUNT=$(ls -1 /app/staticfiles/ 2>/dev/null | wc -l)
        echo "  - Archivos estáticos: $STATIC_COUNT directorios/archivos"
        
        # Asegurar permisos correctos
        if [ -d "/app/staticfiles" ]; then
            chmod -R 755 /app/staticfiles/ 2>/dev/null || true
        fi
        if [ -d "/app/media" ]; then
            chmod -R 755 /app/media/ 2>/dev/null || true
        fi
        
        echo "  - Estaticos recolectados y permisos configurados!"
    fi
else
    echo "  - Saltando collectstatic (modo desarrollo)"
fi

# ----------------------------------------------
# Mostrar informacion del entorno
# ----------------------------------------------
echo "[5/5] Informacion del entorno:"
echo "  - DJANGO_ENV: ${DJANGO_ENV:-local}"
echo "  - DEBUG: ${DJANGO_DEBUG:-not set}"
echo "  - Database: ${POSTGRES_HOST:-localhost}:${POSTGRES_PORT:-5432}/${POSTGRES_DB:-new_gym}"

echo "=========================================="
echo "  Iniciando: $@"
echo "=========================================="

# ----------------------------------------------
# Ejecutar el comando principal
# ----------------------------------------------
exec "$@"
