#!/usr/bin/env python
import os
import django

os.environ.setdefault("DJANGO_SETTINGS_MODULE", "config.settings")
django.setup()

from accounts.models import User
from clients.models import Client, ClientMembership
from organizations.models import Gym

email = "demo.cliente@mygym.com"

user = User.objects.get(email=email)

# Buscar el Client asociado
try:
    client = Client.objects.get(user=user)
    memberships = ClientMembership.objects.filter(client=client)
except Client.DoesNotExist:
    client = None
    memberships = ClientMembership.objects.none()

print(f"Usuario: {user.email}")

if client:
    print(f"Cliente encontrado: {client.gym.name}")
    print(f"Membresías de cliente: {memberships.count()}")
else:
    print("NO tiene un registro de Client asociado.")

if client and memberships.exists():
    for m in memberships:
        gym = m.gym
        print(f"\nGimnasio: {gym.name}")
        print(f"URL: http://127.0.0.1:8000/public/gym/{gym.slug}/")
        print(f"Login: http://127.0.0.1:8000/public/gym/{gym.slug}/login/")
else:
    if client:
        gym = client.gym
        print(f"\nUsando gimnasio del Client: {gym.name}")
        print(f"URL: http://127.0.0.1:8000/public/gym/{gym.slug}/")
        print(f"Login: http://127.0.0.1:8000/public/gym/{gym.slug}/login/")
    else:
        print("\nNO tiene membresías de cliente asignadas ni Client asociado.")
        print("Gimnasios disponibles:")
        for gym in Gym.objects.all()[:3]:
            print(f"  - {gym.name} (slug: {gym.slug})")
