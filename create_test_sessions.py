#!/usr/bin/env python
"""Script para crear sesiones de prueba en el horario."""
import os
import sys

os.environ.setdefault("DJANGO_SETTINGS_MODULE", "config.settings.local")

import django
django.setup()

from organizations.models import Gym
from activities.models import Activity, ActivitySession, Room
from staff.models import StaffProfile
from datetime import datetime, timedelta
from django.utils import timezone


def main():
    gym = Gym.objects.get(slug="qombo-madrid-central")
    room = Room.objects.filter(gym=gym).first()
    staff = StaffProfile.objects.filter(gym=gym).first()
    activities = list(Activity.objects.filter(gym=gym, is_visible_online=True))

    print(f"Gimnasio: {gym.name}")
    print(f"Sala: {room.name if room else 'N/A'}")
    print(f"Staff: {staff.user.get_full_name() if staff else 'N/A'}")
    print(f"Actividades: {[a.name for a in activities]}")

    if not activities:
        print("No hay actividades visibles online. Creando...")
        activities_data = [
            ("Spinning", "#FF6B35", 45),
            ("Yoga", "#7CB342", 60),
            ("CrossFit", "#F57C00", 50),
            ("Body Pump", "#8E24AA", 55),
            ("Pilates", "#00ACC1", 50),
            ("Zumba", "#E91E63", 45),
        ]
        for name, color, duration in activities_data:
            activity, created = Activity.objects.get_or_create(
                gym=gym,
                name=name,
                defaults={
                    "description": f"Clase de {name}",
                    "color": color,
                    "duration_minutes": duration,
                    "is_visible_online": True,
                }
            )
            if created:
                print(f"  Creada: {name}")
            activities.append(activity)
    
    if not room:
        print("No hay sala. Creando...")
        room = Room.objects.create(gym=gym, name="Sala Principal", capacity=30)
        print(f"  Creada: {room.name}")

    # Eliminar sesiones existentes
    deleted, _ = ActivitySession.objects.filter(gym=gym).delete()
    print(f"\nSesiones eliminadas: {deleted}")

    # Crear sesiones para los proximos 14 dias
    now = timezone.now()
    today = now.replace(hour=0, minute=0, second=0, microsecond=0)

    # Horarios tipicos
    schedules = [
        ("08:00", "09:00"),
        ("10:00", "11:00"),
        ("12:00", "13:00"),
        ("17:00", "18:00"),
        ("19:00", "20:00"),
        ("20:00", "21:00"),
    ]

    created = 0
    for day_offset in range(14):
        current_day = today + timedelta(days=day_offset)
        day_of_week = current_day.weekday()  # 0=Lunes, 6=Domingo

        # Menos clases los fines de semana
        day_schedules = schedules[:3] if day_of_week >= 5 else schedules

        for i, (start, end) in enumerate(day_schedules):
            activity = activities[i % len(activities)]
            start_hour, start_min = map(int, start.split(":"))
            end_hour, end_min = map(int, end.split(":"))

            start_dt = current_day.replace(hour=start_hour, minute=start_min)
            end_dt = current_day.replace(hour=end_hour, minute=end_min)

            # Solo crear si no ha pasado ya
            if start_dt > now or day_offset > 0:
                session = ActivitySession.objects.create(
                    activity=activity,
                    gym=gym,
                    room=room,
                    staff=staff,
                    start_datetime=start_dt,
                    end_datetime=end_dt,
                    max_capacity=20,
                    status="scheduled",
                )
                created += 1

    print(f"\nSesiones creadas: {created}")

    # Mostrar algunas
    print("\n=== Proximas sesiones ===")
    upcoming = ActivitySession.objects.filter(
        gym=gym, start_datetime__gte=now
    ).order_by("start_datetime")[:10]
    for s in upcoming:
        print(f"  {s.start_datetime.strftime('%d/%m %H:%M')} - {s.activity.name} ({s.status})")


if __name__ == "__main__":
    main()
