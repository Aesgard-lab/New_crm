"""
Servicio de Backups para el CRM.

Proporciona funcionalidad para:
- Backup de base de datos PostgreSQL
- Backup de archivos media
- Subida a S3 (opcional)
- Limpieza de backups antiguos
- Restauracion de backups
"""

import os
import subprocess
import gzip
import shutil
import logging
from datetime import datetime, timedelta
from pathlib import Path
from typing import Optional, List, Tuple

from django.conf import settings

logger = logging.getLogger(__name__)


class BackupService:
    """
    Servicio principal de backups.
    
    Uso:
        service = BackupService()
        
        # Backup completo
        db_path, media_path = service.create_full_backup()
        
        # Solo base de datos
        db_path = service.backup_database()
        
        # Subir a S3
        service.upload_to_s3(db_path)
    """
    
    def __init__(self, backup_dir: Optional[str] = None):
        """
        Inicializa el servicio de backups.
        
        Args:
            backup_dir: Directorio para almacenar backups.
                       Por defecto: BASE_DIR/backups
        """
        self.backup_dir = Path(backup_dir or settings.BASE_DIR / 'backups')
        self.backup_dir.mkdir(parents=True, exist_ok=True)
        
        # Subdirectorios
        self.db_backup_dir = self.backup_dir / 'database'
        self.media_backup_dir = self.backup_dir / 'media'
        self.db_backup_dir.mkdir(exist_ok=True)
        self.media_backup_dir.mkdir(exist_ok=True)
        
        # Configuracion de base de datos
        self.db_config = settings.DATABASES['default']
        
        # Configuracion de retencion
        self.retention_days = int(os.getenv('BACKUP_RETENTION_DAYS', '30'))
        self.keep_weekly = int(os.getenv('BACKUP_KEEP_WEEKLY', '4'))
        self.keep_monthly = int(os.getenv('BACKUP_KEEP_MONTHLY', '3'))
    
    def create_full_backup(self) -> Tuple[Path, Path]:
        """
        Crea un backup completo (DB + media).
        
        Returns:
            Tuple con rutas de backup de DB y media
        """
        logger.info("Iniciando backup completo...")
        
        db_path = self.backup_database()
        media_path = self.backup_media()
        
        logger.info(f"Backup completo finalizado: DB={db_path}, Media={media_path}")
        return db_path, media_path
    
    def backup_database(self, compress: bool = True) -> Path:
        """
        Crea un backup de la base de datos PostgreSQL.
        
        Args:
            compress: Si True, comprime el backup con gzip
            
        Returns:
            Path al archivo de backup
        """
        timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
        filename = f"db_backup_{timestamp}.sql"
        
        if compress:
            filename += '.gz'
        
        backup_path = self.db_backup_dir / filename
        
        logger.info(f"Creando backup de base de datos: {backup_path}")
        
        # Construir comando pg_dump
        env = os.environ.copy()
        env['PGPASSWORD'] = self.db_config['PASSWORD']
        
        cmd = [
            'pg_dump',
            '-h', self.db_config['HOST'],
            '-p', str(self.db_config['PORT']),
            '-U', self.db_config['USER'],
            '-d', self.db_config['NAME'],
            '--no-owner',
            '--no-privileges',
            '-F', 'p',  # Plain text format
        ]
        
        try:
            if compress:
                # Ejecutar pg_dump y comprimir
                process = subprocess.Popen(
                    cmd,
                    stdout=subprocess.PIPE,
                    stderr=subprocess.PIPE,
                    env=env
                )
                
                with gzip.open(backup_path, 'wb') as f:
                    for chunk in iter(lambda: process.stdout.read(8192), b''):
                        f.write(chunk)
                
                _, stderr = process.communicate()
                if process.returncode != 0:
                    raise subprocess.CalledProcessError(
                        process.returncode, cmd, stderr=stderr
                    )
            else:
                # Ejecutar pg_dump sin comprimir
                with open(backup_path, 'w') as f:
                    subprocess.run(
                        cmd,
                        stdout=f,
                        stderr=subprocess.PIPE,
                        env=env,
                        check=True
                    )
            
            size_mb = backup_path.stat().st_size / (1024 * 1024)
            logger.info(f"Backup de DB completado: {backup_path} ({size_mb:.2f} MB)")
            
            return backup_path
            
        except subprocess.CalledProcessError as e:
            logger.error(f"Error en pg_dump: {e.stderr.decode() if e.stderr else str(e)}")
            raise
        except Exception as e:
            logger.error(f"Error creando backup de DB: {e}")
            raise
    
    def backup_media(self) -> Path:
        """
        Crea un backup comprimido de los archivos media.
        
        Returns:
            Path al archivo tar.gz
        """
        media_root = Path(settings.MEDIA_ROOT)
        
        if not media_root.exists():
            logger.warning(f"Directorio media no existe: {media_root}")
            return None
        
        timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
        backup_path = self.media_backup_dir / f"media_backup_{timestamp}.tar.gz"
        
        logger.info(f"Creando backup de media: {backup_path}")
        
        try:
            # Crear archivo tar.gz
            shutil.make_archive(
                str(backup_path).replace('.tar.gz', ''),
                'gztar',
                root_dir=media_root.parent,
                base_dir=media_root.name
            )
            
            size_mb = backup_path.stat().st_size / (1024 * 1024)
            logger.info(f"Backup de media completado: {backup_path} ({size_mb:.2f} MB)")
            
            return backup_path
            
        except Exception as e:
            logger.error(f"Error creando backup de media: {e}")
            raise
    
    def upload_to_s3(self, file_path: Path, bucket_prefix: str = 'backups') -> Optional[str]:
        """
        Sube un archivo de backup a S3.
        
        Args:
            file_path: Ruta al archivo a subir
            bucket_prefix: Prefijo en el bucket S3
            
        Returns:
            URL del archivo en S3 o None si falla
        """
        try:
            import boto3
            from botocore.exceptions import ClientError
        except ImportError:
            logger.warning("boto3 no instalado, saltando upload a S3")
            return None
        
        # Verificar configuracion de S3
        bucket_name = os.getenv('AWS_BACKUP_BUCKET') or os.getenv('AWS_STORAGE_BUCKET_NAME')
        if not bucket_name:
            logger.warning("AWS_BACKUP_BUCKET no configurado")
            return None
        
        try:
            s3_client = boto3.client(
                's3',
                aws_access_key_id=os.getenv('AWS_ACCESS_KEY_ID'),
                aws_secret_access_key=os.getenv('AWS_SECRET_ACCESS_KEY'),
                region_name=os.getenv('AWS_S3_REGION_NAME', 'eu-west-1')
            )
            
            # Generar key en S3
            date_prefix = datetime.now().strftime('%Y/%m/%d')
            s3_key = f"{bucket_prefix}/{date_prefix}/{file_path.name}"
            
            logger.info(f"Subiendo a S3: s3://{bucket_name}/{s3_key}")
            
            s3_client.upload_file(
                str(file_path),
                bucket_name,
                s3_key,
                ExtraArgs={
                    'StorageClass': 'STANDARD_IA',  # Mas economico para backups
                    'ServerSideEncryption': 'AES256'
                }
            )
            
            s3_url = f"s3://{bucket_name}/{s3_key}"
            logger.info(f"Upload completado: {s3_url}")
            
            return s3_url
            
        except ClientError as e:
            logger.error(f"Error subiendo a S3: {e}")
            return None
    
    def cleanup_old_backups(self) -> int:
        """
        Elimina backups antiguos segun politica de retencion.
        
        Politica:
        - Mantiene backups diarios de los ultimos N dias
        - Mantiene 1 backup semanal de las ultimas N semanas
        - Mantiene 1 backup mensual de los ultimos N meses
        
        Returns:
            Numero de archivos eliminados
        """
        logger.info("Limpiando backups antiguos...")
        deleted_count = 0
        
        now = datetime.now()
        cutoff_daily = now - timedelta(days=self.retention_days)
        
        for backup_dir in [self.db_backup_dir, self.media_backup_dir]:
            backups = sorted(backup_dir.glob('*_backup_*'), reverse=True)
            
            # Agrupar por semana y mes para retencion
            weekly_kept = set()
            monthly_kept = set()
            
            for backup_file in backups:
                # Extraer fecha del nombre del archivo
                try:
                    date_str = backup_file.stem.split('_')[-2]  # YYYYMMDD
                    file_date = datetime.strptime(date_str, '%Y%m%d')
                except (ValueError, IndexError):
                    continue
                
                week_key = file_date.strftime('%Y-W%W')
                month_key = file_date.strftime('%Y-%m')
                
                # Decidir si mantener
                keep = False
                
                # Mantener si es reciente
                if file_date >= cutoff_daily:
                    keep = True
                
                # Mantener un backup semanal
                elif week_key not in weekly_kept and len(weekly_kept) < self.keep_weekly:
                    weekly_kept.add(week_key)
                    keep = True
                
                # Mantener un backup mensual
                elif month_key not in monthly_kept and len(monthly_kept) < self.keep_monthly:
                    monthly_kept.add(month_key)
                    keep = True
                
                if not keep:
                    logger.info(f"Eliminando backup antiguo: {backup_file}")
                    backup_file.unlink()
                    deleted_count += 1
        
        logger.info(f"Limpieza completada: {deleted_count} archivos eliminados")
        return deleted_count
    
    def list_backups(self) -> List[dict]:
        """
        Lista todos los backups disponibles.
        
        Returns:
            Lista de diccionarios con info de cada backup
        """
        backups = []
        
        for backup_dir in [self.db_backup_dir, self.media_backup_dir]:
            for backup_file in backup_dir.glob('*_backup_*'):
                stat = backup_file.stat()
                backups.append({
                    'path': str(backup_file),
                    'name': backup_file.name,
                    'type': 'database' if 'db_' in backup_file.name else 'media',
                    'size_bytes': stat.st_size,
                    'size_mb': round(stat.st_size / (1024 * 1024), 2),
                    'created': datetime.fromtimestamp(stat.st_ctime),
                    'modified': datetime.fromtimestamp(stat.st_mtime),
                })
        
        return sorted(backups, key=lambda x: x['created'], reverse=True)
    
    def restore_database(self, backup_path: Path) -> bool:
        """
        Restaura la base de datos desde un backup.
        
        ⚠️ CUIDADO: Esto sobreescribe la base de datos actual!
        
        Args:
            backup_path: Ruta al archivo de backup
            
        Returns:
            True si la restauracion fue exitosa
        """
        backup_path = Path(backup_path)
        
        if not backup_path.exists():
            raise FileNotFoundError(f"Backup no encontrado: {backup_path}")
        
        logger.warning(f"⚠️ Restaurando base de datos desde: {backup_path}")
        
        env = os.environ.copy()
        env['PGPASSWORD'] = self.db_config['PASSWORD']
        
        # Determinar si esta comprimido
        is_compressed = backup_path.suffix == '.gz'
        
        try:
            if is_compressed:
                # Descomprimir y restaurar
                process = subprocess.Popen(
                    ['psql',
                     '-h', self.db_config['HOST'],
                     '-p', str(self.db_config['PORT']),
                     '-U', self.db_config['USER'],
                     '-d', self.db_config['NAME'],
                     '-q'],  # Quiet mode
                    stdin=subprocess.PIPE,
                    stderr=subprocess.PIPE,
                    env=env
                )
                
                with gzip.open(backup_path, 'rb') as f:
                    process.stdin.write(f.read())
                
                process.stdin.close()
                _, stderr = process.communicate()
                
                if process.returncode != 0:
                    raise subprocess.CalledProcessError(
                        process.returncode, 'psql', stderr=stderr
                    )
            else:
                # Restaurar directamente
                with open(backup_path, 'r') as f:
                    subprocess.run(
                        ['psql',
                         '-h', self.db_config['HOST'],
                         '-p', str(self.db_config['PORT']),
                         '-U', self.db_config['USER'],
                         '-d', self.db_config['NAME'],
                         '-q'],
                        stdin=f,
                        stderr=subprocess.PIPE,
                        env=env,
                        check=True
                    )
            
            logger.info("✅ Restauracion de base de datos completada")
            return True
            
        except subprocess.CalledProcessError as e:
            logger.error(f"Error en restauracion: {e.stderr.decode() if e.stderr else str(e)}")
            raise
        except Exception as e:
            logger.error(f"Error restaurando DB: {e}")
            raise
