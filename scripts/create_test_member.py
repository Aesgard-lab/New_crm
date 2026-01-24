import os
import django

os.environ.setdefault("DJANGO_SETTINGS_MODULE", "config.settings")
django.setup()

from django.contrib.auth import get_user_model
from clients.models import Client
from organizations.models import Gym

User = get_user_model()

def create_test_member():
    email = "socio@gym.com"
    password = "password123"
    
    gym = Gym.objects.first()
    if not gym:
        print("No gyms found. Create a gym first.")
        return

    # Create User
    user, created = User.objects.get_or_create(username=email, defaults={
        "email": email,
        "first_name": "Socio",
        "last_name": "Ejemplo"
    })
    if created:
        user.set_password(password)
        user.save()
        print(f"Usuario creado: {email} / {password}")
    else:
        print(f"Usuario ya existe: {email}")

    # Create Client Profile
    client, created = Client.objects.get_or_create(gym=gym, email=email, defaults={
        "first_name": "Socio",
        "last_name": "Ejemplo",
        "user": user,
        "status": "ACTIVE"
    })
    
    if not client.user:
        client.user = user
        client.save()
        print("Vinculado usuario a cliente.")
        
    print("Test Member listo para probar '/app/login/'")

if __name__ == "__main__":
    create_test_member()
