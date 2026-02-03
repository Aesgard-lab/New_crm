#!/usr/bin/env python
import os
import django

os.environ.setdefault("DJANGO_SETTINGS_MODULE", "config.settings")
django.setup()

from django.db import connection

with connection.cursor() as cursor:
    cursor.execute("ALTER TABLE organizations_gym ADD COLUMN IF NOT EXISTS slug VARCHAR(200) DEFAULT ''")
    print("✓ Campo slug agregado")
    
    cursor.execute("CREATE INDEX IF NOT EXISTS organizations_gym_slug_idx ON organizations_gym(slug)")
    print("✓ Índice creado")

print("\n✓ Campo slug configurado manualmente")
