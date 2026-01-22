import os
import django
os.environ.setdefault("DJANGO_SETTINGS_MODULE", "config.settings")
django.setup()

from staff.models import StaffProfile
from organizations.models import Gym
from django.contrib.auth import get_user_model

User = get_user_model()

print("--- Gyms ---")
for g in Gym.objects.all():
    print(f"Gym: {g.name} (ID: {g.id})")

print("\n--- Users ---")
for u in User.objects.all():
    print(f"User: {u.email} (ID: {u.id})")

print("\n--- Staff Profiles ---")
profiles = StaffProfile.objects.all()
if not profiles:
    print("No StaffProfiles found.")
else:
    for p in profiles:
        print(f"Staff: {p.user.email}, Gym: {p.gym.name} (Gym ID: {p.gym.id}), Active: {p.is_active}")
