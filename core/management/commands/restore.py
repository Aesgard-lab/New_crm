"""
Comando de Django para restaurar backups.

Uso:
    # Listar backups disponibles
    python manage.py restore --list
    
    # Restaurar ultimo backup de DB
    python manage.py restore --latest
    
    # Restaurar backup especifico
    python manage.py restore /path/to/backup.sql.gz
    
    # Restaurar sin confirmacion (cuidado!)
    python manage.py restore --latest --force
"""

import sys
from pathlib import Path

from django.core.management.base import BaseCommand, CommandError
from core.backup_service import BackupService


class Command(BaseCommand):
    help = 'Restaurar base de datos desde un backup'
    
    def add_arguments(self, parser):
        parser.add_argument(
            'backup_file',
            nargs='?',
            type=str,
            help='Ruta al archivo de backup'
        )
        parser.add_argument(
            '--list', '-l',
            action='store_true',
            help='Listar backups de DB disponibles'
        )
        parser.add_argument(
            '--latest',
            action='store_true',
            help='Restaurar el backup mas reciente'
        )
        parser.add_argument(
            '--force', '-f',
            action='store_true',
            help='No pedir confirmacion'
        )
        parser.add_argument(
            '--dry-run',
            action='store_true',
            help='Mostrar que se haria sin ejecutar'
        )
    
    def handle(self, *args, **options):
        service = BackupService()
        
        if options['list']:
            self._list_db_backups(service)
            return
        
        if options['latest']:
            backup_path = self._get_latest_backup(service)
        elif options['backup_file']:
            backup_path = Path(options['backup_file'])
        else:
            raise CommandError(
                "Especifica --list, --latest, o proporciona la ruta del backup"
            )
        
        self._restore_backup(service, backup_path, options)
    
    def _list_db_backups(self, service):
        """Listar backups de base de datos."""
        backups = service.list_backups()
        db_backups = [b for b in backups if b['type'] == 'database']
        
        if not db_backups:
            self.stdout.write(self.style.WARNING(
                "No hay backups de base de datos disponibles"
            ))
            return
        
        self.stdout.write(f"\nBackups de DB disponibles ({len(db_backups)}):\n")
        self.stdout.write("-" * 80)
        
        for i, backup in enumerate(db_backups, 1):
            self.stdout.write(
                f"[{i}] {backup['created'].strftime('%Y-%m-%d %H:%M')} | "
                f"{backup['size_mb']:8.2f} MB | {backup['name']}"
            )
        
        self.stdout.write("-" * 80)
        self.stdout.write(f"\nPara restaurar: python manage.py restore [RUTA_BACKUP]")
    
    def _get_latest_backup(self, service):
        """Obtener el backup mas reciente."""
        backups = service.list_backups()
        db_backups = [b for b in backups if b['type'] == 'database']
        
        if not db_backups:
            raise CommandError("No hay backups de base de datos disponibles")
        
        # El primero es el mas reciente
        latest = db_backups[0]
        return latest['path']
    
    def _restore_backup(self, service, backup_path, options):
        """Restaurar desde un backup."""
        backup_path = Path(backup_path)
        
        # Verificar que existe
        if not backup_path.exists():
            raise CommandError(f"Backup no encontrado: {backup_path}")
        
        # Mostrar informacion del backup
        size_mb = backup_path.stat().st_size / (1024 * 1024)
        self.stdout.write(f"\n{'='*60}")
        self.stdout.write(f"Backup a restaurar:")
        self.stdout.write(f"  Archivo: {backup_path.name}")
        self.stdout.write(f"  Tamano: {size_mb:.2f} MB")
        self.stdout.write(f"{'='*60}\n")
        
        if options['dry_run']:
            self.stdout.write(self.style.WARNING(
                "[DRY-RUN] Se restauraria este backup sin ejecutar cambios"
            ))
            return
        
        # Pedir confirmacion
        if not options['force']:
            self.stdout.write(self.style.ERROR(
                "⚠️  ADVERTENCIA: Esta operacion reemplazara TODOS los datos actuales!"
            ))
            self.stdout.write(self.style.ERROR(
                "⚠️  No hay forma de deshacer esta accion.\n"
            ))
            
            confirm = input("Escribe 'RESTAURAR' para continuar: ")
            if confirm != 'RESTAURAR':
                self.stdout.write(self.style.WARNING("Operacion cancelada"))
                return
        
        # Ejecutar restauracion
        self.stdout.write("\nRestaurando base de datos...")
        self.stdout.write("(Esto puede tardar varios minutos dependiendo del tamano)")
        
        try:
            service.restore_database(str(backup_path))
            self.stdout.write("")
            self.stdout.write(self.style.SUCCESS("=" * 60))
            self.stdout.write(self.style.SUCCESS(
                "✓ Base de datos restaurada correctamente"
            ))
            self.stdout.write(self.style.SUCCESS("=" * 60))
            self.stdout.write("")
            self.stdout.write("Recomendaciones post-restauracion:")
            self.stdout.write("  1. Reiniciar la aplicacion")
            self.stdout.write("  2. Verificar datos importantes")
            self.stdout.write("  3. Ejecutar: python manage.py check")
        except Exception as e:
            raise CommandError(f"Error durante la restauracion: {e}")
