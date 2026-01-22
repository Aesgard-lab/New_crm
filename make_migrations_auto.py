"""
Script para crear migraciones automáticamente sin input del usuario
"""
import os
import sys
import django

# Setup Django
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'config.settings')
django.setup()

from django.core.management import call_command

# Hacer migraciones sin input
try:
    call_command('makemigrations', '--noinput')
    print("\n✅ Migraciones creadas exitosamente")
except Exception as e:
    print(f"\n❌ Error: {e}")
    sys.exit(1)
