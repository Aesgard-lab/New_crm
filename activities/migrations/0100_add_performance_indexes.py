"""
Migracion de indices para activities (sesiones y reservas).
"""
from django.db import migrations, models


class Migration(migrations.Migration):
    
    dependencies = [
        ('activities', '0013_add_spot_booking'),  # Última migración antes de ésta
    ]
    
    operations = [
        # ==================== ACTIVITY SESSION INDEXES ====================
        # Indice principal para calendario: gym + fecha + status
        migrations.AddIndex(
            model_name='activitysession',
            index=models.Index(
                fields=['gym', 'start_datetime', 'status'],
                name='session_calendar_idx'
            ),
        ),
        # Indice para filtrado por actividad
        migrations.AddIndex(
            model_name='activitysession',
            index=models.Index(
                fields=['activity', 'start_datetime'],
                name='session_activity_date_idx'
            ),
        ),
        # Indice para filtrado por staff
        migrations.AddIndex(
            model_name='activitysession',
            index=models.Index(
                fields=['staff', 'start_datetime'],
                name='session_staff_date_idx'
            ),
        ),
        # Indice para filtrado por sala
        migrations.AddIndex(
            model_name='activitysession',
            index=models.Index(
                fields=['room', 'start_datetime'],
                name='session_room_date_idx'
            ),
        ),
        
        # ==================== BOOKING INDEXES ====================
        # Indice para reservas por cliente
        migrations.AddIndex(
            model_name='activitysessionbooking',
            index=models.Index(
                fields=['client', 'status'],
                name='booking_client_status_idx'
            ),
        ),
        # Indice para estado de asistencia
        migrations.AddIndex(
            model_name='activitysessionbooking',
            index=models.Index(
                fields=['session', 'attendance_status'],
                name='booking_attendance_idx'
            ),
        ),
        # Indice para reservas recientes
        migrations.AddIndex(
            model_name='activitysessionbooking',
            index=models.Index(
                fields=['-booked_at'],
                name='booking_recent_idx'
            ),
        ),
    ]
