"""
Script para crear migraciones de asistencia
"""
import os
import sys

if __name__ == "__main__":
    os.system('C:/Users/santi/OneDrive/Escritorio/New_crm/.venv/Scripts/python.exe manage.py makemigrations activities memberships --name add_attendance_fields')
    print("\n✅ Migraciones creadas")
    print("\nAhora ejecuta: python manage.py migrate")
