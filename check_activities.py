#!/usr/bin/env python
"""Verificar actividades y sesiones para la PWA"""
import os
import django
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'core.settings')
django.setup()

from activities.models import Activity, ActivitySession
from gyms.models import Gym
from django.utils import timezone

# Buscar el gym de prueba
gym = Gym.objects.filter(public_slug='qombo-madrid-central').first()
if not gym:
    gym = Gym.objects.first()
    
print(f"Gym: {gym}")
print(f"Slug: {gym.public_slug if gym else 'N/A'}")
print()

# Ver actividades
activities = Activity.objects.filter(gym=gym)
print(f"Total actividades: {activities.count()}")

for a in activities[:5]:
    print(f"  - {a.name}")
    print(f"    is_visible_online: {a.is_visible_online}")
    print(f"    color: {a.color}")
    
print()

# Ver sesiones futuras
now = timezone.now()
sessions = ActivitySession.objects.filter(
    gym=gym,
    start_datetime__gte=now
).select_related('activity')

print(f"Sesiones futuras: {sessions.count()}")

# Sesiones con actividad visible online
visible_sessions = sessions.filter(activity__is_visible_online=True)
print(f"Sesiones con actividad visible online: {visible_sessions.count()}")

# Si hay sesiones pero ninguna visible, activar las actividades
if sessions.exists() and not visible_sessions.exists():
    print()
    print("⚠️ Hay sesiones pero ninguna actividad visible. Activando todas...")
    Activity.objects.filter(gym=gym).update(is_visible_online=True)
    print("✅ Actividades actualizadas")
    
    # Verificar de nuevo
    visible_sessions = ActivitySession.objects.filter(
        gym=gym,
        start_datetime__gte=now,
        activity__is_visible_online=True
    )
    print(f"Sesiones visibles después de actualizar: {visible_sessions.count()}")

# Mostrar algunas sesiones
print()
print("Próximas 5 sesiones:")
for s in sessions[:5]:
    print(f"  - {s.activity.name} @ {s.start_datetime} (visible: {s.activity.is_visible_online})")
