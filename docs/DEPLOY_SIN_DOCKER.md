# 🚀 Despliegue SIN Docker (Bare Metal / VPS)

## ¿Por qué sin Docker?

Cuando el servidor usa **virtualización anidada** (Docker dentro de una VM),
el overhead es significativo: cada contenedor Docker añade ~50-100MB de RAM base
más la capa de virtualización. Con 5-7 contenedores, se pueden consumir
**2-3GB solo en overhead** antes de que la aplicación haga nada.

**Ejecutar directamente en el servidor elimina todo ese overhead.**

---

## Requisitos mínimos

| Recurso | Mínimo | Recomendado |
|---------|--------|-------------|
| CPU     | 1 core | 2 cores     |
| RAM     | 1 GB   | 2 GB        |
| Disco   | 5 GB   | 10 GB       |
| OS      | Ubuntu 22.04+ / Debian 12+ | Ubuntu 24.04 |

---

## 1. Instalar dependencias del sistema

```bash
# Actualizar sistema
sudo apt update && sudo apt upgrade -y

# Python 3.12
sudo apt install -y software-properties-common
sudo add-apt-repository -y ppa:deadsnakes/ppa
sudo apt install -y python3.12 python3.12-venv python3.12-dev

# PostgreSQL
sudo apt install -y postgresql postgresql-contrib

# Redis (ligero, para Celery)
sudo apt install -y redis-server

# Nginx
sudo apt install -y nginx

# Dependencias de compilación
sudo apt install -y build-essential libpq-dev curl
```

## 2. Configurar PostgreSQL

```bash
sudo -u postgres psql <<EOF
CREATE USER crm_user WITH PASSWORD 'tu_password_seguro';
CREATE DATABASE crm_db OWNER crm_user;
ALTER USER crm_user CREATEDB;
\q
EOF
```

**Optimizar PostgreSQL para pocos recursos** (`/etc/postgresql/*/main/postgresql.conf`):
```ini
shared_buffers = 128MB
effective_cache_size = 256MB
maintenance_work_mem = 64MB
work_mem = 4MB
max_connections = 30
checkpoint_completion_target = 0.9
```

```bash
sudo systemctl restart postgresql
```

## 3. Configurar Redis (mínimos recursos)

Editar `/etc/redis/redis.conf`:
```ini
maxmemory 50mb
maxmemory-policy allkeys-lru
save ""
appendonly no
```

```bash
sudo systemctl restart redis-server
```

## 4. Crear usuario y desplegar aplicación

```bash
# Crear usuario de la aplicación
sudo useradd -m -s /bin/bash crm
sudo mkdir -p /opt/crm
sudo chown crm:crm /opt/crm

# Cambiar al usuario
sudo su - crm

# Clonar o copiar el proyecto
cd /opt/crm
# git clone <tu-repo> app
# O copiar los archivos manualmente

# Crear entorno virtual
python3.12 -m venv venv
source venv/bin/activate

# Instalar dependencias
pip install --upgrade pip
pip install -r app/requirements.txt

# Crear archivo de configuración
cat > /opt/crm/.env <<'EOF'
DJANGO_ENV=production
DJANGO_DEBUG=False
DJANGO_SECRET_KEY=genera-una-clave-secreta-aqui
DJANGO_ALLOWED_HOSTS=tu-dominio.com,www.tu-dominio.com
CSRF_TRUSTED_ORIGINS=https://tu-dominio.com

POSTGRES_DB=crm_db
POSTGRES_USER=crm_user
POSTGRES_PASSWORD=tu_password_seguro
POSTGRES_HOST=127.0.0.1
POSTGRES_PORT=5432

REDIS_URL=redis://127.0.0.1:6379/1
CELERY_BROKER_URL=redis://127.0.0.1:6379/0

EMAIL_HOST=smtp.tuproveedor.com
EMAIL_PORT=587
EMAIL_HOST_USER=tu@email.com
EMAIL_HOST_PASSWORD=tu_password_email
EMAIL_USE_TLS=True
DEFAULT_FROM_EMAIL=tu@email.com
EOF

# Migraciones y static files
cd /opt/crm/app
source /opt/crm/venv/bin/activate
python manage.py migrate --noinput
python manage.py collectstatic --noinput
```

## 5. Crear servicios systemd

### 5a. Gunicorn (Django)

```bash
sudo tee /etc/systemd/system/crm-web.service <<'EOF'
[Unit]
Description=CRM Django (Gunicorn)
After=network.target postgresql.service redis-server.service
Requires=postgresql.service

[Service]
Type=notify
User=crm
Group=crm
WorkingDirectory=/opt/crm/app
EnvironmentFile=/opt/crm/.env
ExecStart=/opt/crm/venv/bin/gunicorn config.wsgi:application \
    --bind 127.0.0.1:8000 \
    --workers 2 \
    --worker-class sync \
    --timeout 120 \
    --max-requests 500 \
    --max-requests-jitter 50 \
    --keep-alive 5 \
    --log-level warning \
    --access-logfile /opt/crm/logs/access.log \
    --error-logfile /opt/crm/logs/error.log
ExecReload=/bin/kill -s HUP $MAINPID
Restart=always
RestartSec=5
KillMode=mixed
PrivateTmp=true
NoNewPrivileges=true

# Límites de recursos
MemoryMax=512M
CPUQuota=80%

[Install]
WantedBy=multi-user.target
EOF
```

### 5b. Celery Worker + Beat (combinados)

```bash
sudo tee /etc/systemd/system/crm-celery.service <<'EOF'
[Unit]
Description=CRM Celery Worker + Beat
After=network.target postgresql.service redis-server.service
Requires=postgresql.service redis-server.service

[Service]
Type=forking
User=crm
Group=crm
WorkingDirectory=/opt/crm/app
EnvironmentFile=/opt/crm/.env
ExecStart=/opt/crm/venv/bin/celery -A config worker \
    --beat \
    --scheduler django_celery_beat.schedulers:DatabaseScheduler \
    --loglevel WARNING \
    --concurrency 1 \
    --max-tasks-per-child 100 \
    --without-gossip \
    --without-mingle \
    --without-heartbeat \
    --detach \
    --pidfile=/opt/crm/celery.pid \
    --logfile=/opt/crm/logs/celery.log
ExecStop=/bin/kill -s TERM $MAINPID
Restart=always
RestartSec=10

# Límites de recursos
MemoryMax=384M
CPUQuota=50%

[Install]
WantedBy=multi-user.target
EOF
```

### 5c. Activar servicios

```bash
# Crear directorio de logs
sudo mkdir -p /opt/crm/logs
sudo chown crm:crm /opt/crm/logs

# Activar servicios
sudo systemctl daemon-reload
sudo systemctl enable crm-web crm-celery
sudo systemctl start crm-web crm-celery

# Verificar
sudo systemctl status crm-web
sudo systemctl status crm-celery
```

## 6. Configurar Nginx

```bash
sudo tee /etc/nginx/sites-available/crm <<'EOF'
server {
    listen 80;
    server_name tu-dominio.com www.tu-dominio.com;

    client_max_body_size 20M;

    # Static files
    location /static/ {
        alias /opt/crm/app/staticfiles/;
        expires 30d;
        add_header Cache-Control "public, immutable";
        access_log off;
    }

    # Media files
    location /media/ {
        alias /opt/crm/app/media/;
        expires 7d;
        access_log off;
    }

    # Django app
    location / {
        proxy_pass http://127.0.0.1:8000;
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
        proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto $scheme;
        proxy_redirect off;
    }
}
EOF

sudo ln -sf /etc/nginx/sites-available/crm /etc/nginx/sites-enabled/
sudo rm -f /etc/nginx/sites-enabled/default
sudo nginx -t
sudo systemctl restart nginx
```

### SSL con Let's Encrypt (opcional pero recomendado)

```bash
sudo apt install -y certbot python3-certbot-nginx
sudo certbot --nginx -d tu-dominio.com -d www.tu-dominio.com
```

## 7. Script de actualización

Crear `/opt/crm/update.sh`:
```bash
#!/bin/bash
set -e
cd /opt/crm/app
source /opt/crm/venv/bin/activate

echo "Actualizando código..."
git pull origin main

echo "Instalando dependencias..."
pip install -r requirements.txt

echo "Migraciones..."
python manage.py migrate --noinput

echo "Static files..."
python manage.py collectstatic --noinput

echo "Reiniciando servicios..."
sudo systemctl restart crm-web crm-celery

echo "✓ Actualización completada"
```

---

## Comparativa de consumo de recursos

| Método | Contenedores | RAM base | RAM total estimada |
|--------|-------------|----------|-------------------|
| `docker-compose.prod.yml` | 7 | ~800MB overhead | 3-4 GB |
| `docker-compose.lightweight.yml` | 4 | ~400MB overhead | 1.5-2 GB |
| `docker-compose.single.yml` | 2 | ~150MB overhead | 1-1.5 GB |
| **Sin Docker (este método)** | **0** | **~0MB overhead** | **700MB-1GB** |

---

## Comandos útiles

```bash
# Ver estado de los servicios
sudo systemctl status crm-web crm-celery

# Ver logs en tiempo real
sudo journalctl -u crm-web -f
sudo journalctl -u crm-celery -f

# Reiniciar
sudo systemctl restart crm-web crm-celery

# Ver uso de memoria
ps aux --sort=-%mem | head -20
free -h
```
