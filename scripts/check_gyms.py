import os
import django

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'config.settings')
django.setup()

from organizations.models import Gym

gyms = Gym.objects.all()
print(f"Total de gimnasios: {gyms.count()}")
for gym in gyms:
    print(f"  - ID: {gym.id} | Nombre: {gym.name} | Ciudad: {gym.city} | Activo: {gym.is_active}")
