"""
Tareas Celery para backups automaticos.
"""

import logging
from celery import shared_task
from django.conf import settings

logger = logging.getLogger(__name__)


@shared_task(
    name='core.backup_database',
    bind=True,
    max_retries=3,
    default_retry_delay=300,  # 5 minutos
    autoretry_for=(Exception,),
    acks_late=True,
)
def backup_database_task(self):
    """
    Tarea para crear backup de base de datos.
    
    Ejecutar manualmente:
        backup_database_task.delay()
    
    Programar en Celery Beat:
        Diariamente a las 3:00 AM
    """
    from core.backup_service import BackupService
    
    logger.info("Iniciando tarea de backup de base de datos...")
    
    try:
        service = BackupService()
        backup_path = service.backup_database()
        
        # Subir a S3 si esta configurado
        s3_url = service.upload_to_s3(backup_path, bucket_prefix='backups/database')
        
        result = {
            'status': 'success',
            'backup_path': str(backup_path),
            's3_url': s3_url,
            'size_mb': round(backup_path.stat().st_size / (1024 * 1024), 2),
        }
        
        logger.info(f"Backup de DB completado: {result}")
        return result
        
    except Exception as e:
        logger.error(f"Error en backup de DB: {e}")
        raise


@shared_task(
    name='core.backup_media',
    bind=True,
    max_retries=2,
    default_retry_delay=600,  # 10 minutos
    autoretry_for=(Exception,),
    acks_late=True,
)
def backup_media_task(self):
    """
    Tarea para crear backup de archivos media.
    
    Ejecutar manualmente:
        backup_media_task.delay()
    
    Programar en Celery Beat:
        Semanalmente los domingos a las 4:00 AM
    """
    from core.backup_service import BackupService
    
    logger.info("Iniciando tarea de backup de media...")
    
    try:
        service = BackupService()
        backup_path = service.backup_media()
        
        if backup_path is None:
            return {'status': 'skipped', 'reason': 'No media directory'}
        
        # Subir a S3 si esta configurado
        s3_url = service.upload_to_s3(backup_path, bucket_prefix='backups/media')
        
        result = {
            'status': 'success',
            'backup_path': str(backup_path),
            's3_url': s3_url,
            'size_mb': round(backup_path.stat().st_size / (1024 * 1024), 2),
        }
        
        logger.info(f"Backup de media completado: {result}")
        return result
        
    except Exception as e:
        logger.error(f"Error en backup de media: {e}")
        raise


@shared_task(
    name='core.full_backup',
    bind=True,
    max_retries=2,
    default_retry_delay=600,
)
def full_backup_task(self, upload_to_s3: bool = True):
    """
    Tarea para crear backup completo (DB + media).
    
    Args:
        upload_to_s3: Si subir los backups a S3
    """
    from core.backup_service import BackupService
    
    logger.info("Iniciando backup completo...")
    
    try:
        service = BackupService()
        db_path, media_path = service.create_full_backup()
        
        result = {
            'status': 'success',
            'database': {
                'path': str(db_path),
                'size_mb': round(db_path.stat().st_size / (1024 * 1024), 2),
            },
            'media': {
                'path': str(media_path) if media_path else None,
                'size_mb': round(media_path.stat().st_size / (1024 * 1024), 2) if media_path else 0,
            }
        }
        
        if upload_to_s3:
            result['database']['s3_url'] = service.upload_to_s3(db_path, 'backups/database')
            if media_path:
                result['media']['s3_url'] = service.upload_to_s3(media_path, 'backups/media')
        
        logger.info(f"Backup completo finalizado: {result}")
        return result
        
    except Exception as e:
        logger.error(f"Error en backup completo: {e}")
        raise


@shared_task(name='core.cleanup_old_backups')
def cleanup_old_backups_task():
    """
    Tarea para limpiar backups antiguos.
    
    Programar en Celery Beat:
        Diariamente a las 5:00 AM
    """
    from core.backup_service import BackupService
    
    logger.info("Iniciando limpieza de backups antiguos...")
    
    try:
        service = BackupService()
        deleted_count = service.cleanup_old_backups()
        
        result = {
            'status': 'success',
            'deleted_count': deleted_count,
        }
        
        logger.info(f"Limpieza completada: {result}")
        return result
        
    except Exception as e:
        logger.error(f"Error en limpieza: {e}")
        raise


# ==============================================
# CONFIGURACION DE CELERY BEAT
# ==============================================
# Añadir al admin de Django o ejecutar manualmente:
#
# from django_celery_beat.models import PeriodicTask, CrontabSchedule
#
# # Backup diario de DB a las 3:00 AM
# schedule_db, _ = CrontabSchedule.objects.get_or_create(
#     minute='0', hour='3', day_of_week='*',
#     day_of_month='*', month_of_year='*'
# )
# PeriodicTask.objects.update_or_create(
#     name='Backup diario de base de datos',
#     defaults={
#         'task': 'core.backup_database',
#         'crontab': schedule_db,
#         'enabled': True,
#     }
# )
#
# # Backup semanal de media los domingos a las 4:00 AM
# schedule_media, _ = CrontabSchedule.objects.get_or_create(
#     minute='0', hour='4', day_of_week='0',
#     day_of_month='*', month_of_year='*'
# )
# PeriodicTask.objects.update_or_create(
#     name='Backup semanal de media',
#     defaults={
#         'task': 'core.backup_media',
#         'crontab': schedule_media,
#         'enabled': True,
#     }
# )
#
# # Limpieza diaria a las 5:00 AM
# schedule_cleanup, _ = CrontabSchedule.objects.get_or_create(
#     minute='0', hour='5', day_of_week='*',
#     day_of_month='*', month_of_year='*'
# )
# PeriodicTask.objects.update_or_create(
#     name='Limpieza de backups antiguos',
#     defaults={
#         'task': 'core.cleanup_old_backups',
#         'crontab': schedule_cleanup,
#         'enabled': True,
#     }
# )
