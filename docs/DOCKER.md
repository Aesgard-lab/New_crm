# Docker - Guia de Uso

## Estructura de Archivos

```
├── Dockerfile              # Build de la imagen
├── docker-compose.yml      # Desarrollo local
├── docker-compose.prod.yml # Produccion
├── .dockerignore           # Archivos a excluir
└── docker/
    ├── entrypoint.sh       # Script de inicio
    └── nginx/
        ├── nginx.conf      # Config principal Nginx
        └── conf.d/
            └── default.conf # Config del servidor
```

## Desarrollo Local

### Iniciar todos los servicios

```bash
# Construir e iniciar
docker-compose up -d --build

# Ver logs
docker-compose logs -f

# Ver logs de un servicio especifico
docker-compose logs -f web
```

### Comandos utiles

```bash
# Ejecutar migraciones
docker-compose exec web python manage.py migrate

# Crear superusuario
docker-compose exec web python manage.py createsuperuser

# Acceder al shell de Django
docker-compose exec web python manage.py shell

# Acceder al contenedor
docker-compose exec web bash

# Detener servicios
docker-compose down

# Detener y eliminar volumenes (BORRA DATOS!)
docker-compose down -v
```

### Acceso

- **Web**: http://localhost:8000
- **PostgreSQL**: localhost:5432
- **Redis**: localhost:6379

## Produccion

### Pre-requisitos

1. Configurar variables de entorno en `.env`:

```bash
cp .env.example .env
# Editar .env con valores de produccion
```

2. Generar certificados SSL (primera vez):

```bash
# Crear directorios
mkdir -p docker/certbot/conf docker/certbot/www

# Obtener certificado inicial (reemplaza tudominio.com)
docker-compose -f docker-compose.prod.yml run --rm certbot certonly \
    --webroot -w /var/www/certbot \
    -d tudominio.com -d www.tudominio.com \
    --email tu@email.com --agree-tos --no-eff-email
```

### Desplegar

```bash
# Construir imagenes
docker-compose -f docker-compose.prod.yml build

# Iniciar servicios
docker-compose -f docker-compose.prod.yml up -d

# Ver estado
docker-compose -f docker-compose.prod.yml ps

# Ver logs
docker-compose -f docker-compose.prod.yml logs -f
```

### Actualizar aplicacion

```bash
# Pull cambios del repo
git pull origin main

# Reconstruir y reiniciar
docker-compose -f docker-compose.prod.yml build web celery celery-beat
docker-compose -f docker-compose.prod.yml up -d --no-deps web celery celery-beat
```

### Backup de base de datos

```bash
# Crear backup
docker-compose -f docker-compose.prod.yml exec db \
    pg_dump -U $POSTGRES_USER $POSTGRES_DB > backup_$(date +%Y%m%d).sql

# Restaurar backup
docker-compose -f docker-compose.prod.yml exec -T db \
    psql -U $POSTGRES_USER $POSTGRES_DB < backup_20260124.sql
```

## Troubleshooting

### El contenedor no inicia

```bash
# Ver logs detallados
docker-compose logs --tail=100 web

# Verificar estado de salud
docker-compose ps
```

### Error de conexion a base de datos

```bash
# Verificar que db esta corriendo
docker-compose ps db

# Verificar variables de entorno
docker-compose exec web env | grep POSTGRES
```

### Error de permisos en archivos

```bash
# Ajustar permisos
sudo chown -R 1000:1000 media/ staticfiles/ logs/
```

### Limpiar todo y empezar de cero

```bash
# ATENCION: Esto borra TODOS los datos
docker-compose down -v
docker system prune -af
docker volume prune -f
```

## Variables de Entorno Requeridas

### Desarrollo (docker-compose.yml)
La mayoria tiene valores por defecto, pero puedes personalizar en `.env`.

### Produccion (docker-compose.prod.yml)
**OBLIGATORIAS:**
- `DJANGO_SECRET_KEY`
- `DJANGO_ALLOWED_HOSTS`
- `POSTGRES_DB`, `POSTGRES_USER`, `POSTGRES_PASSWORD`
- `REDIS_PASSWORD` (opcional pero recomendado)

**RECOMENDADAS:**
- `SENTRY_DSN`
- `EMAIL_HOST`, `EMAIL_HOST_USER`, `EMAIL_HOST_PASSWORD`
- `STRIPE_*` (si usas pagos)

## Recursos

- [Docker Documentation](https://docs.docker.com/)
- [Docker Compose](https://docs.docker.com/compose/)
- [Django Docker Best Practices](https://docs.djangoproject.com/en/5.0/howto/deployment/checklist/)
