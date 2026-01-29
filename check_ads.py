import os
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'config.settings')
import django
django.setup()

from marketing.models import Advertisement
from django.utils import timezone

ads = Advertisement.objects.all()
print(f'Total ads: {ads.count()}')
for ad in ads:
    print(f'  ID: {ad.id}')
    print(f'  Title: {ad.title}')
    print(f'  Active: {ad.is_active}')
    print(f'  Position: {ad.position}')
    print(f'  Screens: {ad.target_screens}')
    gyms = list(ad.target_gyms.values_list('name', flat=True))
    print(f'  Gyms: {gyms}')
    print(f'  Start: {ad.start_date}')
    print(f'  End: {ad.end_date}')
    now = timezone.now()
    valid = ad.start_date <= now and (ad.end_date is None or ad.end_date >= now)
    print(f'  Date valid: {valid}')
    print()
