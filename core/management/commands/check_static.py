"""
Management command para verificar configuración de archivos estáticos y media.

Uso: python manage.py check_static
"""
import os
from pathlib import Path

from django.conf import settings
from django.core.management.base import BaseCommand
from django.contrib.staticfiles import finders


class Command(BaseCommand):
    help = 'Verifica la configuración de archivos estáticos y media'

    def add_arguments(self, parser):
        parser.add_argument(
            '--fix',
            action='store_true',
            help='Intenta corregir problemas encontrados',
        )

    def handle(self, *args, **options):
        self.stdout.write(self.style.HTTP_INFO('=' * 50))
        self.stdout.write(self.style.HTTP_INFO('  Verificación de Static/Media Files'))
        self.stdout.write(self.style.HTTP_INFO('=' * 50))
        self.stdout.write('')

        errors = []
        warnings = []

        # 1. Verificar configuración básica
        self.stdout.write(self.style.MIGRATE_HEADING('[1/5] Configuración básica'))
        
        self.stdout.write(f'  STATIC_URL: {settings.STATIC_URL}')
        self.stdout.write(f'  STATIC_ROOT: {settings.STATIC_ROOT}')
        self.stdout.write(f'  MEDIA_URL: {settings.MEDIA_URL}')
        self.stdout.write(f'  MEDIA_ROOT: {settings.MEDIA_ROOT}')
        
        if not settings.STATIC_URL.startswith('/'):
            errors.append('STATIC_URL debe empezar con /')
        if not settings.MEDIA_URL.startswith('/'):
            errors.append('MEDIA_URL debe empezar con /')

        # 2. Verificar directorios
        self.stdout.write('')
        self.stdout.write(self.style.MIGRATE_HEADING('[2/5] Directorios'))
        
        static_root = Path(settings.STATIC_ROOT)
        media_root = Path(settings.MEDIA_ROOT)
        
        if static_root.exists():
            file_count = sum(1 for _ in static_root.rglob('*') if _.is_file())
            self.stdout.write(self.style.SUCCESS(f'  ✓ STATIC_ROOT existe ({file_count} archivos)'))
        else:
            warnings.append(f'STATIC_ROOT no existe: {static_root}')
            self.stdout.write(self.style.WARNING(f'  ⚠ STATIC_ROOT no existe'))
            if options['fix']:
                static_root.mkdir(parents=True, exist_ok=True)
                self.stdout.write(self.style.SUCCESS(f'    → Creado'))

        if media_root.exists():
            file_count = sum(1 for _ in media_root.rglob('*') if _.is_file())
            self.stdout.write(self.style.SUCCESS(f'  ✓ MEDIA_ROOT existe ({file_count} archivos)'))
        else:
            warnings.append(f'MEDIA_ROOT no existe: {media_root}')
            self.stdout.write(self.style.WARNING(f'  ⚠ MEDIA_ROOT no existe'))
            if options['fix']:
                media_root.mkdir(parents=True, exist_ok=True)
                self.stdout.write(self.style.SUCCESS(f'    → Creado'))

        # 3. Verificar STATICFILES_DIRS
        self.stdout.write('')
        self.stdout.write(self.style.MIGRATE_HEADING('[3/5] STATICFILES_DIRS'))
        
        for static_dir in settings.STATICFILES_DIRS:
            static_path = Path(static_dir)
            if static_path.exists():
                self.stdout.write(self.style.SUCCESS(f'  ✓ {static_dir}'))
            else:
                warnings.append(f'Directorio estático no existe: {static_dir}')
                self.stdout.write(self.style.WARNING(f'  ⚠ {static_dir} (no existe)'))

        # 4. Verificar permisos (Linux/Docker)
        self.stdout.write('')
        self.stdout.write(self.style.MIGRATE_HEADING('[4/5] Permisos'))
        
        if static_root.exists():
            if os.access(static_root, os.R_OK):
                self.stdout.write(self.style.SUCCESS(f'  ✓ STATIC_ROOT legible'))
            else:
                errors.append('STATIC_ROOT no es legible')
                self.stdout.write(self.style.ERROR(f'  ✗ STATIC_ROOT no es legible'))
        
        if media_root.exists():
            if os.access(media_root, os.W_OK):
                self.stdout.write(self.style.SUCCESS(f'  ✓ MEDIA_ROOT escribible'))
            else:
                errors.append('MEDIA_ROOT no es escribible')
                self.stdout.write(self.style.ERROR(f'  ✗ MEDIA_ROOT no es escribible'))

        # 5. Verificar whitenoise (producción)
        self.stdout.write('')
        self.stdout.write(self.style.MIGRATE_HEADING('[5/5] WhiteNoise'))
        
        if 'whitenoise.middleware.WhiteNoiseMiddleware' in settings.MIDDLEWARE:
            self.stdout.write(self.style.SUCCESS('  ✓ WhiteNoise configurado'))
            
            # Verificar STATICFILES_STORAGE
            storage = getattr(settings, 'STATICFILES_STORAGE', 'default')
            self.stdout.write(f'  Storage: {storage}')
        else:
            warnings.append('WhiteNoise no está en MIDDLEWARE')
            self.stdout.write(self.style.WARNING('  ⚠ WhiteNoise no configurado'))

        # Resumen
        self.stdout.write('')
        self.stdout.write(self.style.HTTP_INFO('=' * 50))
        
        if errors:
            self.stdout.write(self.style.ERROR(f'  ✗ {len(errors)} errores encontrados'))
            for error in errors:
                self.stdout.write(self.style.ERROR(f'    - {error}'))
        
        if warnings:
            self.stdout.write(self.style.WARNING(f'  ⚠ {len(warnings)} advertencias'))
            for warning in warnings:
                self.stdout.write(self.style.WARNING(f'    - {warning}'))
        
        if not errors and not warnings:
            self.stdout.write(self.style.SUCCESS('  ✓ Todo OK!'))
        
        self.stdout.write(self.style.HTTP_INFO('=' * 50))
        
        if errors:
            self.stdout.write('')
            self.stdout.write('Para corregir, ejecuta:')
            self.stdout.write('  python manage.py collectstatic --noinput')
            return
        
        self.stdout.write('')
        self.stdout.write('Si los archivos no se ven en producción:')
        self.stdout.write('  1. Verifica que Nginx apunte a /app/staticfiles/')
        self.stdout.write('  2. Verifica volúmenes en docker-compose.prod.yml')
        self.stdout.write('  3. Ejecuta: docker exec crm_web_prod python manage.py collectstatic --noinput')
