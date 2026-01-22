import os
import django
import random
from datetime import timedelta
from django.utils import timezone

# Setup Django
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'config.settings')
django.setup()

from organizations.models import Franchise, Gym
from accounts.models import User
from clients.models import Client, ClientSale

def create_data():
    print("--- Generando Datos para Dashboard de Franquicia (Qombo) ---")

    # 1. Create Owner
    owner_email = "owner@qombo.com"
    owner, created = User.objects.get_or_create(email=owner_email)
    if created:
        owner.set_password("qombo123")
        owner.first_name = "Sr. Qombo"
        owner.save()
        print(f"[OK] Usuario Owner creado: {owner_email} / qombo123")
    else:
        print(f"[INFO] Usuario Owner ya existe: {owner_email}")

    # 2. Create Franchise
    franchise, created = Franchise.objects.get_or_create(name="Qombo Fitness Group")
    if created:
        print("[OK] Franquicia 'Qombo Fitness Group' creada.")
    
    franchise.owners.add(owner)
    print("[OK] Owner asignado a la franquicia.")

    # 3. Create Gyms
    gyms_data = [
        {"name": "Qombo Madrid Central", "city": "Madrid", "perf": 1.5}, # partial multiplier for random
        {"name": "Qombo Barcelona Beach", "city": "Barcelona", "perf": 1.2},
        {"name": "Qombo Valencia City", "city": "Valencia", "perf": 0.9},
        {"name": "Qombo Sevilla Sur", "city": "Sevilla", "perf": 0.7},
    ]

    for g_data in gyms_data:
        gym, created = Gym.objects.get_or_create(
            franchise=franchise,
            name=g_data["name"],
            defaults={
                "commercial_name": g_data["name"],
                "city": g_data["city"],
                "country": "España"
            }
        )
        if created:
            print(f"[OK] Gym creado: {gym.name}")
        
        # 4. Generate Clients
        # Clear existing for cleanliness in dev? No, just add.
        
        # Active Members
        num_active = int(random.randint(100, 300) * g_data["perf"])
        print(f"   > Generando {num_active} socios activos para {gym.name}...")
        
        for i in range(num_active):
            Client.objects.create(
                gym=gym,
                first_name=f"Socio {i}",
                last_name=f"Activo {gym.city[:3]}",
                status=Client.Status.ACTIVE,
                email=f"active{i}_{gym.id}@test.com"
            )

        # Churn (Inactive)
        num_inactive = int(num_active * random.uniform(0.05, 0.15)) # 5-15% churn
        for i in range(num_inactive):
            Client.objects.create(
                gym=gym,
                first_name=f"Socio {i}",
                last_name=f"Baja {gym.city[:3]}",
                status=Client.Status.INACTIVE,
                email=f"inactive{i}_{gym.id}@test.com"
            )
            
        # 5. Generate Sales (Revenue History)
        # Last 6 months
        print(f"   > Generando historial de ventas...")
        today = timezone.now()
        
        # Get a random active client to assign sales to (simplification)
        dummy_client, _ = Client.objects.get_or_create(
            gym=gym, 
            email=f"payer_{gym.id}@qombo.com", 
            defaults={"first_name": "Cliente", "last_name": "Generico"}
        )

        for i in range(180): # last 6 months days
            day_date = today - timedelta(days=i)
            # Random daily sales count
            daily_tx = random.randint(1, 5)
            
            for _ in range(daily_tx):
                amount = random.choice([29.90, 49.90, 300.00]) * g_data["perf"]
                # Add some randomness
                amount = round(amount * random.uniform(0.9, 1.1), 2)
                
                s = ClientSale.objects.create(
                    client=dummy_client,
                    concept="Cuota Mensual" if amount < 60 else "Bono Anual",
                    amount=amount,
                )
                # Hack to set date in past (auto_now_add usually overrides, but we can update after or force)
                s.date = day_date
                s.save()

    print("\n[SUCCESS] Datos generados correctamente.")
    print("------------------------------------------------")
    print("URL Dashboard: http://127.0.0.1:8000/organizations/franchise/dashboard/")
    print(f"Usuario: {owner_email}")
    print("Password: qombo123")
    print("------------------------------------------------")

if __name__ == "__main__":
    create_data()
