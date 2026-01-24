"""
Script para crear anuncios de ejemplo en el sistema de marketing.
Ejecutar: python create_demo_advertisements.py
"""

import os
import django

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'config.settings')
django.setup()

from marketing.models import Advertisement
from organizations.models import Gym
from accounts.models import User
from django.utils import timezone
from datetime import timedelta

def create_demo_advertisements():
    """Crea anuncios de ejemplo para probar el sistema"""
    
    # Obtener primer gimnasio y usuario admin
    gym = Gym.objects.first()
    admin_user = User.objects.filter(is_superuser=True).first()
    
    if not gym or not admin_user:
        print("❌ No se encontró gimnasio o usuario admin")
        return
    
    print(f"🏋️ Creando anuncios para: {gym.name}")
    print(f"👤 Usuario creador: {admin_user.email}")
    
    # Limpiar anuncios anteriores de demo
    Advertisement.objects.filter(title__startswith='[DEMO]').delete()
    
    advertisements = [
        {
            'title': '[DEMO] Black Friday - 50% OFF',
            'position': Advertisement.PositionType.HERO_CAROUSEL,
            'ad_type': Advertisement.AdType.INTERNAL_PROMO,
            'cta_text': '¡Aprovecha Ahora!',
            'cta_action': Advertisement.ActionType.VIEW_CATALOG,
            'target_screens': ['HOME', 'SHOP'],
            'priority': 1,
            'duration_seconds': 5,
        },
        {
            'title': '[DEMO] Nueva Clase de Yoga',
            'position': Advertisement.PositionType.HERO_CAROUSEL,
            'ad_type': Advertisement.AdType.INTERNAL_PROMO,
            'cta_text': 'Reserva tu Plaza',
            'cta_action': Advertisement.ActionType.BOOK_CLASS,
            'cta_url': '123',  # ID de clase de ejemplo
            'target_screens': ['HOME', 'CLASS_CATALOG'],
            'priority': 2,
            'duration_seconds': 5,
        },
        {
            'title': '[DEMO] Suplementos Deportivos',
            'position': Advertisement.PositionType.INLINE_MIDDLE,
            'ad_type': Advertisement.AdType.SPONSOR,
            'cta_text': 'Ver Productos',
            'cta_action': Advertisement.ActionType.VIEW_CATALOG,
            'target_screens': ['SHOP', 'PROFILE'],
            'priority': 1,
            'duration_seconds': 5,
        },
        {
            'title': '[DEMO] Entrenamiento Personal',
            'position': Advertisement.PositionType.HERO_CAROUSEL,
            'ad_type': Advertisement.AdType.CROSS_SELL,
            'cta_text': 'Más Información',
            'cta_action': Advertisement.ActionType.VIEW_PROMO,
            'target_screens': ['PROFILE', 'CLASS_CATALOG'],
            'priority': 3,
            'duration_seconds': 5,
        },
        {
            'title': '[DEMO] Únete a Nuestro Reto 30 Días',
            'position': Advertisement.PositionType.HERO_CAROUSEL,
            'ad_type': Advertisement.AdType.EDUCATIONAL,
            'cta_text': 'Unirse al Reto',
            'cta_action': Advertisement.ActionType.EXTERNAL_URL,
            'cta_url': 'https://ejemplo.com/reto-30-dias',
            'target_screens': ['HOME'],
            'priority': 4,
            'duration_seconds': 7,
        },
    ]
    
    created_count = 0
    
    for ad_data in advertisements:
        # Crear anuncio sin imagen (se puede agregar manualmente después)
        ad = Advertisement.objects.create(
            gym=gym,
            title=ad_data['title'],
            position=ad_data['position'],
            ad_type=ad_data['ad_type'],
            cta_text=ad_data['cta_text'],
            cta_action=ad_data['cta_action'],
            cta_url=ad_data.get('cta_url', ''),
            target_screens=ad_data['target_screens'],
            start_date=timezone.now(),
            end_date=timezone.now() + timedelta(days=30),
            priority=ad_data['priority'],
            duration_seconds=ad_data['duration_seconds'],
            is_active=True,
            created_by=admin_user,
        )
        
        created_count += 1
        screens_str = ', '.join(ad_data['target_screens'])
        print(f"✅ {ad.title}")
        print(f"   Pantallas: {screens_str}")
        print(f"   CTA: {ad.cta_text} → {ad.get_cta_action_display()}")
        print()
    
    print(f"🎉 Se crearon {created_count} anuncios de ejemplo")
    print()
    print("⚠️  IMPORTANTE:")
    print("   - Los anuncios no tienen imágenes asignadas")
    print("   - Ve a /marketing/advertisements/ para agregar imágenes")
    print("   - Recomendación: 1080x600px para HERO_CAROUSEL")
    print()
    print("📱 Para probar en la app Flutter:")
    print("   - Asegúrate de que el servidor Django esté corriendo")
    print("   - Los anuncios aparecerán automáticamente en las pantallas configuradas")
    print("   - Pantalla HOME: Muestra anuncios con target_screens=['HOME']")
    print("   - Pantalla SHOP: Muestra anuncios con target_screens=['SHOP']")

if __name__ == '__main__':
    create_demo_advertisements()
