# 🚀 Guía de Despliegue para Servidor Pequeño

## El Problema

Tu servidor tiene **virtualización anidada** (VM dentro de VM) + Docker, lo cual causa:
- Overhead de CPU de 30-50%
- Overhead de memoria adicional
- I/O más lento

La configuración original (`docker-compose.prod.yml`) ejecuta:
- **6 contenedores** separados
- **4 workers Gunicorn** × 2 threads = 8 procesos Django
- **4 workers Celery** + 1 Beat = 5 procesos
- Total: ~20+ procesos compitiendo por recursos

### ¿Es culpa de Django?

**NO directamente**. Django es eficiente. El problema es la combinación de:

1. **Virtualización anidada** (el factor más grande)
2. **Librerías pesadas** instaladas (pandas ~100MB, matplotlib, weasyprint)
3. **Múltiples contenedores** con overhead cada uno
4. **Features de auditoría** que corren en cada save()

## La Solución

### Opción A: Configuración Docker Ligera

El archivo `docker-compose.lightweight.yml` reduce a:
- **4 contenedores** (sin Nginx, sin Celery Beat separado)
- **2 workers Gunicorn** = 2 procesos Django
- **1 worker Celery** con Beat integrado = 1 proceso
- Total: ~8 procesos
- **Límites de memoria** en cada contenedor

### Opción B: Optimizaciones de Código (Adicional)

Activar modo lightweight en Django añadiendo al `.env`:

```bash
# Activar modo bajo recursos
LIGHTWEIGHT_MODE=True
DISABLE_AUDIT_SIGNALS=True
CELERY_EAGER=True  # Ejecuta tareas síncronamente (sin Celery)
```

Y en `settings.py` al final:

```python
import os
if os.getenv('LIGHTWEIGHT_MODE') == 'True':
    from .settings_lightweight import *  # noqa
```

### Requisitos Mínimos
- **CPU**: 2 cores (4 recomendado)
- **RAM**: 2 GB (4 GB recomendado)
- **Disco**: 10 GB

---

## 📋 Instrucciones de Despliegue

### 1. Preparar el servidor

```bash
# Actualizar sistema
sudo apt update && sudo apt upgrade -y

# Instalar Docker (si no está)
curl -fsSL https://get.docker.com | sh
sudo usermod -aG docker $USER

# Instalar Docker Compose
sudo apt install docker-compose-plugin -y
```

### 2. Subir el proyecto

```bash
# Clonar o copiar el proyecto
cd /opt
git clone <tu-repositorio> crm
cd crm
```

### 3. Configurar variables de entorno

```bash
# Crear archivo .env
cat > .env << 'EOF'
# Base de datos
POSTGRES_DB=crm_production
POSTGRES_USER=crm_user
POSTGRES_PASSWORD=TU_PASSWORD_SEGURA_AQUI

# Django
DJANGO_SECRET_KEY=genera-una-clave-secreta-larga-y-aleatoria-aqui
DJANGO_ALLOWED_HOSTS=tudominio.com,www.tudominio.com
CSRF_TRUSTED_ORIGINS=https://tudominio.com,https://www.tudominio.com

# Redis (opcional, dejar vacío si no quieres password)
REDIS_PASSWORD=

# Email (configura según tu proveedor)
EMAIL_HOST=smtp.gmail.com
EMAIL_PORT=587
EMAIL_HOST_USER=tu-email@gmail.com
EMAIL_HOST_PASSWORD=tu-app-password
EMAIL_USE_TLS=True
DEFAULT_FROM_EMAIL=noreply@tudominio.com

# Stripe (si usas pagos)
STRIPE_SECRET_KEY=
STRIPE_PUBLISHABLE_KEY=
STRIPE_WEBHOOK_SECRET=

# Sentry (opcional, para monitoreo de errores)
SENTRY_DSN=
EOF
```

### 4. Desplegar

```bash
# Construir imagen
docker compose -f docker-compose.lightweight.yml build

# Levantar servicios
docker compose -f docker-compose.lightweight.yml up -d

# Ver logs
docker compose -f docker-compose.lightweight.yml logs -f

# Ejecutar migraciones
docker compose -f docker-compose.lightweight.yml exec web python manage.py migrate

# Crear superusuario
docker compose -f docker-compose.lightweight.yml exec web python manage.py createsuperuser

# Collectstatic
docker compose -f docker-compose.lightweight.yml exec web python manage.py collectstatic --noinput
```

### 5. Verificar estado

```bash
# Ver contenedores corriendo
docker compose -f docker-compose.lightweight.yml ps

# Ver uso de recursos
docker stats

# Ver logs de errores
docker compose -f docker-compose.lightweight.yml logs web --tail=100
```

---

## 🔧 Configuración de Nginx (en el Host)

En lugar de usar Nginx en Docker, instálalo directamente en el servidor:

```bash
sudo apt install nginx -y
```

Crear configuración:

```bash
sudo nano /etc/nginx/sites-available/crm
```

```nginx
server {
    listen 80;
    server_name tudominio.com www.tudominio.com;

    client_max_body_size 10M;

    location /static/ {
        alias /opt/crm/staticfiles/;
        expires 30d;
        add_header Cache-Control "public, immutable";
    }

    location /media/ {
        alias /opt/crm/media/;
        expires 7d;
    }

    location / {
        proxy_pass http://127.0.0.1:80;
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
        proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto $scheme;
        proxy_connect_timeout 60s;
        proxy_read_timeout 120s;
    }
}
```

```bash
# Activar sitio
sudo ln -s /etc/nginx/sites-available/crm /etc/nginx/sites-enabled/
sudo nginx -t
sudo systemctl reload nginx

# SSL con Certbot
sudo apt install certbot python3-certbot-nginx -y
sudo certbot --nginx -d tudominio.com -d www.tudominio.com
```

---

## 📊 Comparación de Recursos

| Configuración | RAM Estimada | CPU Procesos |
|--------------|--------------|--------------|
| `docker-compose.prod.yml` | 4-6 GB | 20+ |
| `docker-compose.lightweight.yml` | 1.5-2 GB | 8 |

---

## ⚠️ Limitaciones del Modo Ligero

1. **Menos concurrencia**: Solo 2 peticiones simultáneas de Django
2. **Celery más lento**: Las tareas se procesan una a una
3. **Sin Nginx integrado**: Debes instalarlo en el host o usar el puerto directamente

---

## 🆘 Solución de Problemas

### Si sigue consumiendo mucha memoria

```bash
# Revisar qué consume más
docker stats --no-stream

# Reducir aún más los workers
# Edita docker-compose.lightweight.yml:
# --workers 1 (en vez de 2)
```

### Si las tareas de Celery se acumulan

```bash
# Ver cola de tareas
docker compose -f docker-compose.lightweight.yml exec celery celery -A config inspect active

# Limpiar cola si es necesario
docker compose -f docker-compose.lightweight.yml exec celery celery -A config purge
```

### Reiniciar todo limpiamente

```bash
docker compose -f docker-compose.lightweight.yml down
docker compose -f docker-compose.lightweight.yml up -d
```

---

## 💡 Recomendación Final

Si el proyecto sigue consumiendo demasiado, considera:

1. **VPS dedicado** en lugar de VM anidada (DigitalOcean, Hetzner, Vultr)
2. **Servicios gestionados**: PostgreSQL y Redis externos (reduce 2 contenedores)
3. **Desactivar Celery** si no necesitas tareas en segundo plano frecuentes
