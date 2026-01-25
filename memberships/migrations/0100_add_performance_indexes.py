"""
Migracion de indices para memberships (planes).
"""
from django.db import migrations, models


class Migration(migrations.Migration):
    
    dependencies = [
        ('memberships', '0006_add_attendance_tracking'),  # Última migración antes de ésta
    ]
    
    operations = [
        # ==================== MEMBERSHIP PLAN INDEXES ====================
        # Indice para planes activos por gym
        migrations.AddIndex(
            model_name='membershipplan',
            index=models.Index(
                fields=['gym', 'is_active'],
                name='plan_gym_active_idx'
            ),
        ),
        # Indice para planes visibles online
        migrations.AddIndex(
            model_name='membershipplan',
            index=models.Index(
                fields=['gym', 'is_visible_online', 'is_active'],
                name='plan_online_visible_idx'
            ),
        ),
        # Indice para ordenamiento
        migrations.AddIndex(
            model_name='membershipplan',
            index=models.Index(
                fields=['gym', 'display_order'],
                name='plan_display_order_idx'
            ),
        ),
    ]
