import os
import django
import sys

sys.path.append(os.getcwd())
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'config.settings')
django.setup()

from organizations.models import Franchise, Gym
from accounts.models import User

def create_demo_branch():
    print("--- Creando Gimnasio Sucursal para Demo ---")
    
    # 1. Find or Create Franchise
    franchise = Franchise.objects.first()
    if not franchise:
        print("No se encontró ninguna franquicia. Creando una por defecto...")
        franchise = Franchise.objects.create(name="Franquicia Demo")
    
    print(f"Usando Franquicia: {franchise.name}")
    
    # 2. Add Superuser as Owner if exists (to ensure visibility if testing as SU)
    superuser = User.objects.filter(is_superuser=True).first()
    if superuser:
        franchise.owners.add(superuser)
        print(f"Superusuario {superuser.email} añadido como Owner de la franquicia.")

    # 3. Create the Branch Gym
    branch_name = "FitChain Sucursal Demo"
    gym, created = Gym.objects.get_or_create(
        name=branch_name,
        franchise=franchise,
        defaults={
            'city': 'Madrid',
            'phone': '555-000-111'
        }
    )
    
    if created:
        print(f"[OK] Gimnasio '{branch_name}' creado exitosamente.")
    else:
        print(f"[INFO] El gimnasio '{branch_name}' ya existía.")
        
    print("\nTodo listo. Ahora puedes ir al Panel de Control > Actividades > Propagar")
    print("y deberías ver 'FitChain Sucursal Demo' en la lista de destinos.")

if __name__ == '__main__':
    create_demo_branch()
