#!/usr/bin/env python
import os
import django

os.environ.setdefault("DJANGO_SETTINGS_MODULE", "config.settings")
django.setup()

from organizations.models import Gym
from django.utils.text import slugify

gyms = Gym.objects.all()
print(f"Generando slugs para {gyms.count()} gimnasios...")

for gym in gyms:
    base_slug = slugify(gym.commercial_name or gym.name)
    slug = base_slug
    counter = 1
    
    while Gym.objects.filter(slug=slug).exclude(pk=gym.pk).exists():
        slug = f"{base_slug}-{counter}"
        counter += 1
    
    gym.slug = slug
    gym.save(update_fields=['slug'])
    print(f"✓ {gym.name} -> {slug}")

print("\n✓ Todos los slugs generados correctamente")
