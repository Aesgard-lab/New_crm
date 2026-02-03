# 🚀 Guía de Operaciones en Producción

Esta guía cubre los procedimientos operacionales críticos para mantener el CRM en producción.

## 📋 Tabla de Contenidos

1. [Despliegue](#despliegue)
2. [Monitoreo](#monitoreo)
3. [Respaldos](#respaldos)
4. [Escalado](#escalado)
5. [Recuperación de Desastres](#recuperación-de-desastres)
6. [Troubleshooting](#troubleshooting)

---

## 🎯 Despliegue

### Requisitos Previos

```bash
# Variables de entorno requeridas
DJANGO_SECRET_KEY=<clave-secreta-única-64-chars>
DATABASE_URL=postgres://user:pass@host:5432/dbname
REDIS_URL=redis://host:6379/0
ALLOWED_HOSTS=tudominio.com,www.tudominio.com
DEBUG=False
```

### Despliegue con Docker Compose

```bash
# 1. Clonar y preparar
git clone <repo> && cd New_crm
cp .env.example .env
# Editar .env con valores de producción

# 2. Construir imágenes
docker-compose -f docker-compose.prod.yml build

# 3. Iniciar servicios
docker-compose -f docker-compose.prod.yml up -d

# 4. Ejecutar migraciones
docker-compose -f docker-compose.prod.yml exec web python manage.py migrate

# 5. Recopilar archivos estáticos
docker-compose -f docker-compose.prod.yml exec web python manage.py collectstatic --noinput

# 6. Crear superusuario (primera vez)
docker-compose -f docker-compose.prod.yml exec web python manage.py createsuperuser
```

### Despliegue Blue-Green (Zero-Downtime)

```bash
# Ver docker-compose.bluegreen.yml para configuración completa
# 1. Desplegar nuevo ambiente "green"
docker-compose -f docker-compose.bluegreen.yml up -d web-green

# 2. Verificar salud
curl http://localhost:8001/health/

# 3. Cambiar tráfico en nginx
# Editar nginx.conf para apuntar a green

# 4. Detener ambiente "blue" viejo
docker-compose -f docker-compose.bluegreen.yml stop web-blue
```

### Despliegue en Kubernetes

```bash
# Aplicar manifiestos
kubectl apply -f k8s/

# Verificar pods
kubectl get pods -n crm

# Ver logs
kubectl logs -f deployment/web -n crm
```

---

## 📊 Monitoreo

### Health Checks

```bash
# Verificar estado de la aplicación
curl https://tudominio.com/health/

# Verificar conectividad de base de datos
docker-compose exec web python manage.py check --database default

# Verificar estado de Celery
docker-compose exec celery celery -A config inspect ping
```

### Logs

```bash
# Ver logs en tiempo real
docker-compose -f docker-compose.prod.yml logs -f web

# Ver logs de Celery
docker-compose -f docker-compose.prod.yml logs -f celery

# Filtrar por error
docker-compose logs web 2>&1 | grep -i error
```

### Métricas con Sentry

Las excepciones se envían automáticamente a Sentry si `SENTRY_DSN` está configurado:

```python
# config/settings.py
SENTRY_DSN = env('SENTRY_DSN', default='')
```

### Comandos de Diagnóstico

```bash
# Diagnóstico de archivos estáticos
docker-compose exec web python manage.py check_static

# Verificar usuarios
docker-compose exec web python scripts/diagnostics/diagnose_users.py

# Verificar configuración de pagos
docker-compose exec web python scripts/diagnostics/check_payment_config.py
```

---

## 💾 Respaldos

### Backup de Base de Datos

```bash
# Backup manual
docker-compose exec db pg_dump -U postgres crm_db > backup_$(date +%Y%m%d_%H%M%S).sql

# Restaurar backup
cat backup_20240115_120000.sql | docker-compose exec -T db psql -U postgres crm_db
```

### Backup Automatizado (Cron)

```bash
# Añadir a crontab
0 2 * * * /path/to/scripts/backup_db.sh >> /var/log/backup.log 2>&1
```

### Script de Backup Completo

```bash
#!/bin/bash
# scripts/backup_full.sh

DATE=$(date +%Y%m%d_%H%M%S)
BACKUP_DIR="/backups"

# Base de datos
docker-compose exec -T db pg_dump -U postgres crm_db > $BACKUP_DIR/db_$DATE.sql

# Media files
tar -czf $BACKUP_DIR/media_$DATE.tar.gz media/

# Retener solo últimos 7 días
find $BACKUP_DIR -type f -mtime +7 -delete

echo "Backup completado: $DATE"
```

### Backup de Media (S3)

```bash
# Sincronizar a S3
aws s3 sync media/ s3://bucket-name/media/ --delete
```

---

## 📈 Escalado

### Escalado Horizontal (Docker Compose)

```bash
# Escalar workers web
docker-compose -f docker-compose.prod.yml up -d --scale web=3

# Escalar Celery workers
docker-compose -f docker-compose.prod.yml up -d --scale celery=5
```

### Escalado en Kubernetes

```bash
# Escalar deployment
kubectl scale deployment/web --replicas=5 -n crm

# Auto-scaling
kubectl autoscale deployment/web --cpu-percent=70 --min=2 --max=10 -n crm
```

### Optimización de Base de Datos

```sql
-- Analizar tablas grandes
VACUUM ANALYZE clients_client;
VACUUM ANALYZE activities_activitysession;
VACUUM ANALYZE clients_clientmembership;

-- Índices recomendados
CREATE INDEX CONCURRENTLY idx_client_gym_status 
ON clients_client(gym_id, status);

CREATE INDEX CONCURRENTLY idx_membership_dates 
ON clients_clientmembership(start_date, end_date);
```

---

## 🔥 Recuperación de Desastres

### Procedimiento de Recuperación

1. **Evaluar el daño**
   ```bash
   # Verificar estado de servicios
   docker-compose ps
   kubectl get pods -n crm
   ```

2. **Restaurar base de datos**
   ```bash
   # Detener aplicación
   docker-compose stop web celery
   
   # Restaurar último backup
   cat /backups/db_latest.sql | docker-compose exec -T db psql -U postgres crm_db
   
   # Reiniciar
   docker-compose up -d
   ```

3. **Verificar integridad**
   ```bash
   docker-compose exec web python manage.py check
   docker-compose exec web python manage.py dbshell <<< "SELECT COUNT(*) FROM clients_client;"
   ```

### RTO y RPO

- **RTO (Recovery Time Objective)**: 1 hora
- **RPO (Recovery Point Objective)**: 24 horas (con backups diarios)

Para RPO menor, configurar replicación PostgreSQL o backups más frecuentes.

---

## 🔧 Troubleshooting

### Problemas Comunes

#### 1. Error 502 Bad Gateway

```bash
# Verificar que web está corriendo
docker-compose ps web

# Ver logs
docker-compose logs --tail=100 web

# Reiniciar
docker-compose restart web
```

#### 2. Archivos Estáticos No Cargan

```bash
# Recopilar estáticos
docker-compose exec web python manage.py collectstatic --clear --noinput

# Verificar permisos
docker-compose exec web ls -la /app/staticfiles/

# Verificar nginx config
docker-compose exec nginx nginx -t
```

#### 3. Celery No Procesa Tareas

```bash
# Ver estado de workers
docker-compose exec celery celery -A config status

# Ver tareas pendientes
docker-compose exec celery celery -A config inspect active

# Reiniciar celery
docker-compose restart celery celery-beat
```

#### 4. Base de Datos Lenta

```bash
# Ver queries lentas
docker-compose exec db psql -U postgres -c "
SELECT query, calls, mean_time 
FROM pg_stat_statements 
ORDER BY mean_time DESC 
LIMIT 10;"

# Ver bloqueos
docker-compose exec db psql -U postgres -c "
SELECT * FROM pg_stat_activity 
WHERE wait_event IS NOT NULL;"
```

#### 5. Memoria Alta

```bash
# Ver uso de memoria por contenedor
docker stats --no-stream

# Reiniciar contenedor problemático
docker-compose restart web

# Limpiar imágenes no usadas
docker system prune -a
```

### Comandos de Emergencia

```bash
# Reiniciar todo
docker-compose -f docker-compose.prod.yml restart

# Detener todo de forma segura
docker-compose -f docker-compose.prod.yml down

# Ver todos los logs
docker-compose -f docker-compose.prod.yml logs --tail=500

# Entrar al contenedor para debug
docker-compose exec web /bin/bash

# Ejecutar Django shell
docker-compose exec web python manage.py shell
```

---

## 📞 Contactos de Emergencia

| Rol | Contacto |
|-----|----------|
| Administrador de Sistema | admin@tudominio.com |
| DBA | dba@tudominio.com |
| Desarrollador On-Call | dev@tudominio.com |

---

## 📝 Checklist Pre-Despliegue

- [ ] Variables de entorno configuradas
- [ ] DEBUG=False
- [ ] ALLOWED_HOSTS configurado
- [ ] SECRET_KEY único y seguro
- [ ] SSL/TLS configurado
- [ ] Backups automatizados
- [ ] Monitoreo activo (Sentry)
- [ ] Health checks configurados
- [ ] Logs centralizados
- [ ] Documentación actualizada
