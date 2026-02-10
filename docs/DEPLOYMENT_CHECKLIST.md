# ✅ Checklist de Deployment para Producción

Este documento contiene la lista de verificación para desplegar el CRM en un servidor de producción.

---

## 📋 Pre-Deployment

### 1. Variables de Entorno (REQUERIDAS)

```bash
# Seguridad (CRÍTICO)
DJANGO_SECRET_KEY=<clave-50-caracteres-minimo>
DJANGO_ALLOWED_HOSTS=tudominio.com,www.tudominio.com
DJANGO_SETTINGS_MODULE=config.settings.production

# Base de Datos PostgreSQL
POSTGRES_DB=crm_production
POSTGRES_USER=crm_user
POSTGRES_PASSWORD=<contraseña-segura>
POSTGRES_HOST=db.tudominio.com
POSTGRES_PORT=5432

# Redis (caché y Celery)
REDIS_URL=redis://localhost:6379/1
CELERY_BROKER_URL=redis://localhost:6379/0

# Email SMTP
EMAIL_HOST=smtp.tudominio.com
EMAIL_PORT=587
EMAIL_USE_TLS=True
EMAIL_HOST_USER=noreply@tudominio.com
EMAIL_HOST_PASSWORD=<contraseña>
DEFAULT_FROM_EMAIL=noreply@tudominio.com

# CORS y CSRF
CORS_ALLOWED_ORIGINS=https://tudominio.com
CSRF_TRUSTED_ORIGINS=https://tudominio.com

# Sentry (Monitoreo de errores)
SENTRY_DSN=https://xxxxx@sentry.io/xxxxx
SENTRY_ENVIRONMENT=production

# Stripe (Pagos)
STRIPE_SECRET_KEY=sk_live_xxxxx
STRIPE_WEBHOOK_SECRET=whsec_xxxxx
STRIPE_PUBLISHABLE_KEY=pk_live_xxxxx

# Backups (opcional)
BACKUP_DIR=/var/backups/crm
BACKUP_RETENTION_DAYS=30
```

### 2. Verificar Configuración

- [ ] `DEBUG = False` en producción
- [ ] `SECRET_KEY` única y segura (no la de desarrollo)
- [ ] `ALLOWED_HOSTS` contiene dominios correctos
- [ ] Certificado SSL/TLS configurado
- [ ] Redis corriendo y accesible
- [ ] PostgreSQL corriendo y accesible

---

## 🔧 Preparación del Servidor

### 3. Instalar Dependencias del Sistema

```bash
# Ubuntu/Debian
sudo apt update
sudo apt install -y python3.12 python3.12-venv python3-pip \
    postgresql-client libpq-dev nginx redis-server \
    supervisor curl git

# Crear usuario de aplicación
sudo useradd -m -s /bin/bash crmuser
sudo mkdir -p /var/www/crm
sudo chown crmuser:crmuser /var/www/crm
```

### 4. Clonar y Configurar Proyecto

```bash
sudo su - crmuser
cd /var/www/crm
git clone <repo-url> .

# Crear entorno virtual
python3.12 -m venv venv
source venv/bin/activate

# Instalar dependencias (SIN face_recognition)
pip install -r requirements.txt
```

### 5. Configurar Variables de Entorno

```bash
# Crear archivo .env
cp .env.example .env
nano .env  # Editar con valores de producción
```

---

## 🗄️ Base de Datos

### 6. Configurar PostgreSQL

```bash
# En el servidor de base de datos
sudo -u postgres psql

CREATE DATABASE crm_production;
CREATE USER crm_user WITH PASSWORD 'contraseña-segura';
GRANT ALL PRIVILEGES ON DATABASE crm_production TO crm_user;
ALTER DATABASE crm_production OWNER TO crm_user;
\q
```

### 7. Ejecutar Migraciones

```bash
source venv/bin/activate
python manage.py migrate
python manage.py collectstatic --noinput
python manage.py createsuperuser
```

---

## 🚀 Configurar Servicios

### 8. Gunicorn (Supervisor)

Crear `/etc/supervisor/conf.d/crm.conf`:

```ini
[program:crm]
command=/var/www/crm/venv/bin/gunicorn config.wsgi:application -c /var/www/crm/gunicorn.conf.py
directory=/var/www/crm
user=crmuser
autostart=true
autorestart=true
stderr_logfile=/var/log/crm/gunicorn.err.log
stdout_logfile=/var/log/crm/gunicorn.out.log
environment=DJANGO_SETTINGS_MODULE="config.settings.production"

[program:crm_celery]
command=/var/www/crm/venv/bin/celery -A config worker -l info
directory=/var/www/crm
user=crmuser
autostart=true
autorestart=true
stderr_logfile=/var/log/crm/celery.err.log
stdout_logfile=/var/log/crm/celery.out.log

[program:crm_celerybeat]
command=/var/www/crm/venv/bin/celery -A config beat -l info
directory=/var/www/crm
user=crmuser
autostart=true
autorestart=true
stderr_logfile=/var/log/crm/celerybeat.err.log
stdout_logfile=/var/log/crm/celerybeat.out.log
```

```bash
sudo mkdir -p /var/log/crm
sudo chown crmuser:crmuser /var/log/crm
sudo supervisorctl reread
sudo supervisorctl update
sudo supervisorctl start all
```

### 9. Nginx (Reverse Proxy)

Crear `/etc/nginx/sites-available/crm`:

```nginx
upstream crm_app {
    server 127.0.0.1:8000;
}

server {
    listen 80;
    server_name tudominio.com www.tudominio.com;
    return 301 https://$server_name$request_uri;
}

server {
    listen 443 ssl http2;
    server_name tudominio.com www.tudominio.com;

    ssl_certificate /etc/letsencrypt/live/tudominio.com/fullchain.pem;
    ssl_certificate_key /etc/letsencrypt/live/tudominio.com/privkey.pem;
    ssl_protocols TLSv1.2 TLSv1.3;
    ssl_ciphers ECDHE-ECDSA-AES128-GCM-SHA256:ECDHE-RSA-AES128-GCM-SHA256;
    ssl_prefer_server_ciphers off;

    client_max_body_size 10M;

    location /static/ {
        alias /var/www/crm/staticfiles/;
        expires 30d;
        add_header Cache-Control "public, immutable";
    }

    location /media/ {
        alias /var/www/crm/media/;
        expires 7d;
    }

    location / {
        proxy_pass http://crm_app;
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
        proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto $scheme;
        proxy_connect_timeout 30s;
        proxy_read_timeout 30s;
    }

    # Health checks
    location /health/ {
        proxy_pass http://crm_app;
        access_log off;
    }
}
```

```bash
sudo ln -s /etc/nginx/sites-available/crm /etc/nginx/sites-enabled/
sudo nginx -t
sudo systemctl reload nginx
```

### 10. SSL con Let's Encrypt

```bash
sudo apt install certbot python3-certbot-nginx
sudo certbot --nginx -d tudominio.com -d www.tudominio.com
```

---

## 🐳 Deployment con Docker (Alternativa)

```bash
# Build
docker build -t crm:latest .

# Run con docker-compose
docker-compose -f docker-compose.prod.yml up -d
```

---

## ✅ Post-Deployment Checklist

### Verificaciones

- [ ] El sitio carga en HTTPS
- [ ] Login funciona correctamente
- [ ] Panel de administración accesible
- [ ] Emails se envían correctamente
- [ ] Celery procesa tareas (verificar logs)
- [ ] Backups automáticos funcionando
- [ ] Sentry recibe errores de prueba

### Pruebas de Funcionalidad

```bash
# Test de endpoint de salud
curl -f https://tudominio.com/health/live/

# Verificar headers de seguridad
curl -I https://tudominio.com | grep -E "(Strict|Content-Security|X-Frame)"

# Verificar estado de servicios
sudo supervisorctl status
```

### Monitoreo

- [ ] Dashboard de Sentry configurado
- [ ] Alertas de errores activadas
- [ ] Monitoreo de recursos del servidor
- [ ] Logs centralizados (opcional)

---

## 🔄 Actualizaciones

```bash
# Pull cambios
cd /var/www/crm
git pull origin main

# Activar entorno
source venv/bin/activate

# Actualizar dependencias
pip install -r requirements.txt

# Migraciones
python manage.py migrate

# Recolectar estáticos
python manage.py collectstatic --noinput

# Reiniciar servicios
sudo supervisorctl restart crm crm_celery crm_celerybeat
```

---

## ⚠️ Notas Importantes

### Módulo de Reconocimiento Facial (DESACTIVADO)

El módulo `facial_checkin` ha sido **desactivado** para reducir consumo de recursos:

- Comentado en `INSTALLED_APPS`
- URLs deshabilitadas
- Dependencias `face_recognition` y `dlib` comentadas en `requirements.txt`

Para reactivar, descomentar las líneas correspondientes (requiere ~2GB RAM adicional).

### Selfie Check-in

El módulo de selfie para check-in está **en pruebas**. Funciona de forma independiente al reconocimiento facial (solo almacena fotos como evidencia).

---

## 📞 Contacto de Soporte

Para problemas de deployment, contactar al equipo de desarrollo.

---

*Última actualización: $(date)*
