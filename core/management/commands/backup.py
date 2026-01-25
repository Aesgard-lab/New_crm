"""
Comando de Django para gestionar backups.

Uso:
    # Crear backup de base de datos
    python manage.py backup --database
    
    # Crear backup de media
    python manage.py backup --media
    
    # Backup completo
    python manage.py backup --full
    
    # Listar backups
    python manage.py backup --list
    
    # Limpiar backups antiguos
    python manage.py backup --cleanup
    
    # Restaurar backup
    python manage.py backup --restore /path/to/backup.sql.gz
"""

from django.core.management.base import BaseCommand, CommandError
from core.backup_service import BackupService


class Command(BaseCommand):
    help = 'Gestiona backups de base de datos y media'
    
    def add_arguments(self, parser):
        # Acciones principales
        group = parser.add_mutually_exclusive_group(required=True)
        group.add_argument(
            '--database', '-d',
            action='store_true',
            help='Crear backup de la base de datos'
        )
        group.add_argument(
            '--media', '-m',
            action='store_true',
            help='Crear backup de archivos media'
        )
        group.add_argument(
            '--full', '-f',
            action='store_true',
            help='Crear backup completo (DB + media)'
        )
        group.add_argument(
            '--list', '-l',
            action='store_true',
            help='Listar backups disponibles'
        )
        group.add_argument(
            '--cleanup', '-c',
            action='store_true',
            help='Limpiar backups antiguos'
        )
        group.add_argument(
            '--restore', '-r',
            type=str,
            metavar='PATH',
            help='Restaurar desde un backup'
        )
        
        # Opciones adicionales
        parser.add_argument(
            '--no-compress',
            action='store_true',
            help='No comprimir el backup de DB'
        )
        parser.add_argument(
            '--upload-s3',
            action='store_true',
            help='Subir backup a S3'
        )
        parser.add_argument(
            '--force',
            action='store_true',
            help='Forzar accion sin confirmacion'
        )
    
    def handle(self, *args, **options):
        service = BackupService()
        
        if options['database']:
            self._backup_database(service, options)
        
        elif options['media']:
            self._backup_media(service, options)
        
        elif options['full']:
            self._backup_full(service, options)
        
        elif options['list']:
            self._list_backups(service)
        
        elif options['cleanup']:
            self._cleanup_backups(service)
        
        elif options['restore']:
            self._restore_backup(service, options['restore'], options['force'])
    
    def _backup_database(self, service, options):
        """Crear backup de base de datos."""
        self.stdout.write("Creando backup de base de datos...")
        
        compress = not options['no_compress']
        backup_path = service.backup_database(compress=compress)
        
        size_mb = backup_path.stat().st_size / (1024 * 1024)
        self.stdout.write(self.style.SUCCESS(
            f"✓ Backup creado: {backup_path} ({size_mb:.2f} MB)"
        ))
        
        if options['upload_s3']:
            self._upload_to_s3(service, backup_path)
    
    def _backup_media(self, service, options):
        """Crear backup de media."""
        self.stdout.write("Creando backup de media...")
        
        backup_path = service.backup_media()
        
        if backup_path is None:
            self.stdout.write(self.style.WARNING(
                "⚠ No hay archivos media para respaldar"
            ))
            return
        
        size_mb = backup_path.stat().st_size / (1024 * 1024)
        self.stdout.write(self.style.SUCCESS(
            f"✓ Backup creado: {backup_path} ({size_mb:.2f} MB)"
        ))
        
        if options['upload_s3']:
            self._upload_to_s3(service, backup_path)
    
    def _backup_full(self, service, options):
        """Crear backup completo."""
        self.stdout.write("Creando backup completo...")
        
        db_path, media_path = service.create_full_backup()
        
        self.stdout.write(self.style.SUCCESS("✓ Backup completo creado:"))
        
        db_size = db_path.stat().st_size / (1024 * 1024)
        self.stdout.write(f"  - DB: {db_path} ({db_size:.2f} MB)")
        
        if media_path:
            media_size = media_path.stat().st_size / (1024 * 1024)
            self.stdout.write(f"  - Media: {media_path} ({media_size:.2f} MB)")
        
        if options['upload_s3']:
            self._upload_to_s3(service, db_path)
            if media_path:
                self._upload_to_s3(service, media_path)
    
    def _list_backups(self, service):
        """Listar backups disponibles."""
        backups = service.list_backups()
        
        if not backups:
            self.stdout.write(self.style.WARNING("No hay backups disponibles"))
            return
        
        self.stdout.write(f"\nBackups disponibles ({len(backups)}):\n")
        self.stdout.write("-" * 80)
        
        for backup in backups:
            type_str = backup['type'].upper().ljust(8)
            if backup['type'] == 'database':
                type_display = self.style.HTTP_INFO(type_str)
            else:
                type_display = self.style.HTTP_NOT_MODIFIED(type_str)
            self.stdout.write(
                f"{type_display} | "
                f"{backup['created'].strftime('%Y-%m-%d %H:%M')} | "
                f"{backup['size_mb']:8.2f} MB | "
                f"{backup['name']}"
            )
        
        self.stdout.write("-" * 80)
    
    def _cleanup_backups(self, service):
        """Limpiar backups antiguos."""
        self.stdout.write("Limpiando backups antiguos...")
        
        deleted = service.cleanup_old_backups()
        
        if deleted > 0:
            self.stdout.write(self.style.SUCCESS(
                f"✓ Se eliminaron {deleted} backups antiguos"
            ))
        else:
            self.stdout.write("No hay backups para eliminar")
    
    def _restore_backup(self, service, backup_path, force):
        """Restaurar desde un backup."""
        if not force:
            self.stdout.write(self.style.WARNING(
                "\n⚠️  ADVERTENCIA: Esta accion sobreescribira la base de datos actual!\n"
            ))
            confirm = input("Escribe 'CONFIRMAR' para continuar: ")
            if confirm != 'CONFIRMAR':
                self.stdout.write(self.style.ERROR("Operacion cancelada"))
                return
        
        self.stdout.write(f"Restaurando desde: {backup_path}")
        
        try:
            service.restore_database(backup_path)
            self.stdout.write(self.style.SUCCESS(
                "✓ Base de datos restaurada correctamente"
            ))
        except FileNotFoundError:
            raise CommandError(f"Backup no encontrado: {backup_path}")
        except Exception as e:
            raise CommandError(f"Error restaurando: {e}")
    
    def _upload_to_s3(self, service, file_path):
        """Subir archivo a S3."""
        self.stdout.write(f"Subiendo a S3: {file_path.name}...")
        
        s3_url = service.upload_to_s3(file_path)
        
        if s3_url:
            self.stdout.write(self.style.SUCCESS(f"  ✓ {s3_url}"))
        else:
            self.stdout.write(self.style.WARNING(
                "  ⚠ No se pudo subir a S3 (verificar configuracion)"
            ))
