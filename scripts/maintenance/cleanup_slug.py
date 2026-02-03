#!/usr/bin/env python
import os
import django

os.environ.setdefault("DJANGO_SETTINGS_MODULE", "config.settings")
django.setup()

from django.db import connection

with connection.cursor() as cursor:
    # Eliminar índices problem áticos si existen
    try:
        cursor.execute("DROP INDEX IF EXISTS organizations_gym_slug_d3dd9f47_like CASCADE")
        print("✓ Índice LIKE eliminado")
    except Exception as e:
        print(f"No se pudo eliminar índice LIKE: {e}")
    
    try:
        cursor.execute("DROP INDEX IF EXISTS organizations_gym_slug_d3dd9f47 CASCADE")
        print("✓ Índice slug eliminado")
    except Exception as e:
        print(f"No se pudo eliminar índice slug: {e}")
    
    try:
        cursor.execute("DROP INDEX IF EXISTS organizations_gym_slug_key CASCADE")
        print("✓ Índice UNIQUE eliminado")
    except Exception as e:
        print(f"No se pudo eliminar índice UNIQUE: {e}")
        
    # Eliminar constraint si existe
    try:
        cursor.execute("ALTER TABLE organizations_gym DROP CONSTRAINT IF EXISTS organizations_gym_slug_key CASCADE")
        print("✓ Constraint UNIQUE eliminado")
    except Exception as e:
        print(f"No se pudo eliminar constraint: {e}")

print("\n✓ Limpieza completada")
