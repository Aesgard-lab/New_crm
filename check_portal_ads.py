import os
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'config.settings.local')

import django
django.setup()

from marketing.models import Advertisement, Popup
from organizations.models import Gym
from django.utils import timezone

gym = Gym.objects.get(slug='qombo-madrid-central')
print(f'=== GYM: {gym.name} (ID={gym.id}) ===')
print()

# Check ads
print('=== ANUNCIOS ===')
ads = Advertisement.objects.filter(target_gyms=gym, is_active=True)
print(f'Total anuncios activos para este gym: {ads.count()}')
for ad in ads:
    print(f'  - {ad.title} | Pos: {ad.position} | Screens: {ad.target_screens}')

print()

# Check popups  
print('=== POPUPS ===')
popups = Popup.objects.filter(target_gyms=gym, is_active=True)
print(f'Total popups activos para este gym: {popups.count()}')
for p in popups:
    print(f'  - {p.title} | Start: {p.start_date} | End: {p.end_date}')
