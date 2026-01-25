#!/usr/bin/env python
"""
Django's command-line utility for administrative tasks.

El entorno se selecciona automáticamente según la variable DJANGO_ENV:
    - local (default): Desarrollo
    - staging: Pre-producción
    - production: Producción

Ejemplo de uso:
    # Desarrollo (por defecto)
    python manage.py runserver
    
    # Producción
    DJANGO_ENV=production python manage.py check --deploy
"""
import os
import sys


def main():
    """Run administrative tasks."""
    # El settings module usa __init__.py que lee DJANGO_ENV
    os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'config.settings')
    try:
        from django.core.management import execute_from_command_line
    except ImportError as exc:
        raise ImportError(
            "Couldn't import Django. Are you sure it's installed and "
            "available on your PYTHONPATH environment variable? Did you "
            "forget to activate a virtual environment?"
        ) from exc
    execute_from_command_line(sys.argv)


if __name__ == '__main__':
    main()
