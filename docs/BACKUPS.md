# Sistema de Backups Automaticos

## Descripcion General

El sistema de backups proporciona respaldo automatico y manual de:
- Base de datos PostgreSQL
- Archivos media (subidos por usuarios)

Los backups pueden almacenarse localmente o en Amazon S3.

---

## Configuracion

### Variables de Entorno

```env
# Directorio local para backups (default: /backups)
BACKUP_DIR=/ruta/a/backups

# Retencion de backups (default: 30 dias)
BACKUP_RETENTION_DAYS=30

# Configuracion S3 (opcional)
AWS_ACCESS_KEY_ID=tu-access-key
AWS_SECRET_ACCESS_KEY=tu-secret-key
AWS_S3_BUCKET_NAME=tu-bucket-backups
AWS_S3_REGION_NAME=eu-west-1
```

### Estructura de Directorios

```
/backups/
├── database/           # Backups de PostgreSQL
│   ├── db_backup_20240115_120000.sql.gz
│   └── db_backup_20240114_120000.sql.gz
└── media/              # Backups de archivos media
    ├── media_backup_20240115_120000.tar.gz
    └── media_backup_20240114_120000.tar.gz
```

---

## Uso Manual (Comandos Django)

### Crear Backups

```bash
# Backup solo de base de datos
python manage.py backup --database

# Backup solo de media
python manage.py backup --media

# Backup completo (DB + media)
python manage.py backup --full

# Backup sin compresion
python manage.py backup --database --no-compress

# Backup con subida a S3
python manage.py backup --database --upload-s3
```

### Listar Backups

```bash
python manage.py backup --list
```

Salida ejemplo:
```
Backups disponibles (5):
--------------------------------------------------------------------------------
DATABASE | 2024-01-15 12:00 |    45.32 MB | db_backup_20240115_120000.sql.gz
DATABASE | 2024-01-14 12:00 |    44.89 MB | db_backup_20240114_120000.sql.gz
MEDIA    | 2024-01-15 12:00 |   128.56 MB | media_backup_20240115_120000.tar.gz
--------------------------------------------------------------------------------
```

### Restaurar Backups

```bash
# Ver backups disponibles
python manage.py restore --list

# Restaurar el mas reciente
python manage.py restore --latest

# Restaurar backup especifico
python manage.py restore /backups/database/db_backup_20240115_120000.sql.gz

# Restaurar sin confirmacion (usar con cuidado!)
python manage.py restore --latest --force

# Ver que se haria sin ejecutar
python manage.py restore --latest --dry-run
```

### Limpiar Backups Antiguos

```bash
python manage.py backup --cleanup
```

---

## Backups Automaticos (Celery)

### Configuracion Celery Beat

Los backups automaticos se programan en `config/settings/base.py`:

```python
CELERY_BEAT_SCHEDULE = {
    # Backup diario de DB a las 3:00 AM
    'backup-database-daily': {
        'task': 'core.tasks.backup_database_task',
        'schedule': crontab(hour=3, minute=0),
    },
    # Backup semanal de media los domingos a las 4:00 AM
    'backup-media-weekly': {
        'task': 'core.tasks.backup_media_task',
        'schedule': crontab(hour=4, minute=0, day_of_week='sunday'),
    },
    # Limpieza semanal los lunes a las 5:00 AM
    'cleanup-backups-weekly': {
        'task': 'core.tasks.cleanup_old_backups_task',
        'schedule': crontab(hour=5, minute=0, day_of_week='monday'),
    },
}
```

### Ejecutar Manualmente una Tarea

```bash
# Desde Django shell
python manage.py shell

>>> from core.tasks import backup_database_task
>>> backup_database_task.delay()
```

### Verificar Tareas Programadas

```bash
celery -A config inspect scheduled
```

---

## Almacenamiento en S3

### Configuracion AWS

1. Crear bucket S3 con la siguiente politica:

```json
{
    "Version": "2012-10-17",
    "Statement": [
        {
            "Effect": "Allow",
            "Action": [
                "s3:PutObject",
                "s3:GetObject",
                "s3:DeleteObject",
                "s3:ListBucket"
            ],
            "Resource": [
                "arn:aws:s3:::tu-bucket-backups",
                "arn:aws:s3:::tu-bucket-backups/*"
            ]
        }
    ]
}
```

2. Crear usuario IAM con acceso al bucket

3. Configurar variables de entorno:
```env
AWS_ACCESS_KEY_ID=AKIA...
AWS_SECRET_ACCESS_KEY=...
AWS_S3_BUCKET_NAME=tu-bucket-backups
AWS_S3_REGION_NAME=eu-west-1
```

### Verificar Subida

```bash
# Backup con subida a S3
python manage.py backup --database --upload-s3

# Ver backups en S3
aws s3 ls s3://tu-bucket-backups/backups/database/
```

---

## Docker / Produccion

### Docker Compose

El servicio de backups se incluye en `docker-compose.prod.yml`:

```yaml
services:
  backup:
    build: .
    command: python manage.py backup --database
    volumes:
      - backup_data:/backups
    environment:
      - DJANGO_ENV=production
    depends_on:
      - db
```

### Cron en Host (Alternativa)

Si no usas Celery Beat, puedes programar con cron:

```bash
# Editar crontab
crontab -e

# Backup diario a las 3:00 AM
0 3 * * * cd /app && docker-compose exec -T web python manage.py backup --database

# Backup semanal de media los domingos a las 4:00 AM
0 4 * * 0 cd /app && docker-compose exec -T web python manage.py backup --media

# Limpieza semanal
0 5 * * 1 cd /app && docker-compose exec -T web python manage.py backup --cleanup
```

---

## Restauracion de Emergencia

### Proceso Completo

1. **Detener la aplicacion**
   ```bash
   docker-compose down
   ```

2. **Restaurar base de datos**
   ```bash
   # Desde backup local
   docker-compose run --rm web python manage.py restore --latest --force
   
   # O manualmente con pg_restore
   gunzip < /backups/database/backup.sql.gz | psql -U postgres -d crm_db
   ```

3. **Restaurar media (si aplica)**
   ```bash
   cd /app/media
   tar -xzf /backups/media/media_backup_20240115.tar.gz
   ```

4. **Reiniciar aplicacion**
   ```bash
   docker-compose up -d
   ```

5. **Verificar**
   ```bash
   docker-compose exec web python manage.py check
   ```

### Restaurar desde S3

```bash
# Descargar backup
aws s3 cp s3://tu-bucket/backups/database/db_backup_20240115.sql.gz /backups/

# Restaurar
python manage.py restore /backups/db_backup_20240115.sql.gz
```

---

## Monitoreo y Alertas

### Verificar Ultimo Backup

```bash
python manage.py backup --list | head -5
```

### Script de Verificacion

Crear `/scripts/check_backup.sh`:

```bash
#!/bin/bash

BACKUP_DIR="/backups/database"
MAX_AGE_HOURS=25

# Encontrar backup mas reciente
LATEST=$(ls -t $BACKUP_DIR/*.sql.gz 2>/dev/null | head -1)

if [ -z "$LATEST" ]; then
    echo "ERROR: No hay backups"
    exit 1
fi

# Verificar edad
AGE_MINUTES=$(( ($(date +%s) - $(stat -c %Y "$LATEST")) / 60 ))
AGE_HOURS=$(( AGE_MINUTES / 60 ))

if [ $AGE_HOURS -gt $MAX_AGE_HOURS ]; then
    echo "ALERTA: Ultimo backup tiene $AGE_HOURS horas"
    exit 1
fi

echo "OK: Ultimo backup hace $AGE_HOURS horas - $LATEST"
exit 0
```

### Integracion con Sentry

Los errores de backup se reportan automaticamente a Sentry si esta configurado.

---

## Buenas Practicas

1. **Probar restauracion periodicamente**
   - Al menos una vez al mes, restaurar en entorno de prueba

2. **Multiples ubicaciones**
   - Mantener backups locales Y en S3
   - Considerar replicacion cross-region

3. **Encriptacion**
   - S3 ya encripta en reposo
   - Para backups locales, considerar GPG

4. **Retencion**
   - Diarios: 7 dias
   - Semanales: 4 semanas
   - Mensuales: 12 meses

5. **Alertas**
   - Configurar alerta si backup falla
   - Monitorear espacio en disco

---

## Troubleshooting

### Error: "pg_dump: command not found"

```bash
# Instalar cliente PostgreSQL
apt-get install postgresql-client

# O en Docker, verificar que esta en PATH
which pg_dump
```

### Error: "Permission denied"

```bash
# Verificar permisos del directorio
chmod 755 /backups
chown -R www-data:www-data /backups
```

### Error: "S3 upload failed"

1. Verificar credenciales AWS
2. Verificar permisos del bucket
3. Verificar conectividad de red

```bash
aws s3 ls s3://tu-bucket/
```

### Backup muy lento

- Considerar `pg_dump` con formato custom (`-Fc`)
- Usar compresion paralela
- Programar en horas de baja actividad

---

## API de BackupService

Para uso programatico:

```python
from core.backup_service import BackupService

service = BackupService()

# Crear backup
db_path = service.backup_database(compress=True)
media_path = service.backup_media()

# Subir a S3
s3_url = service.upload_to_s3(db_path)

# Listar backups
backups = service.list_backups()

# Limpiar antiguos
deleted = service.cleanup_old_backups()

# Restaurar
service.restore_database('/path/to/backup.sql.gz')
```
