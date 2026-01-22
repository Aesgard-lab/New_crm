"""
Script para crear un anuncio publicitario de prueba
"""
import os
import django
from django.core.files.base import ContentFile
import requests
from io import BytesIO

os.environ.setdefault('DJANGO_SECRET_KEY', 'dev-secret-key')
os.environ.setdefault('DJANGO_DEBUG', 'True')
os.environ.setdefault('DJANGO_ALLOWED_HOSTS', '127.0.0.1,localhost')

# Setup Django
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'config.settings')
django.setup()

from marketing.models import Advertisement
from organizations.models import Gym
from django.utils import timezone
from datetime import timedelta

def create_test_advertisement():
    # Obtener primer gimnasio
    gym = Gym.objects.first()
    if not gym:
        print("❌ No hay gimnasios en la base de datos")
        return
    
    print(f"🏋️ Usando gimnasio: {gym.name}")
    
    # Descargar imagen de prueba desde placeholder
    print("📥 Descargando imagen de ejemplo...")
    try:
        # Hero carousel: 1080x600
        response = requests.get('https://placehold.co/1080x600/9333ea/ffffff?text=Black+Friday+50%25+OFF&font=roboto')
        image_content = ContentFile(response.content, name='test_ad_hero.png')
        
        # Mobile: 1080x600 también (se podría usar ratio 9:16 para stories)
        response_mobile = requests.get('https://placehold.co/1080x600/9333ea/ffffff?text=50%25+OFF&font=roboto')
        image_mobile_content = ContentFile(response_mobile.content, name='test_ad_mobile.png')
    except Exception as e:
        print(f"⚠️ No se pudo descargar imagen: {e}")
        print("Creando anuncio sin imagen...")
        image_content = None
        image_mobile_content = None
    
    # Crear anuncio
    ad = Advertisement.objects.create(
        gym=gym,
        title="Black Friday 50% OFF - Prueba",
        position=Advertisement.PositionType.HERO_CAROUSEL,
        ad_type=Advertisement.AdType.INTERNAL_PROMO,
        
        # CTA
        cta_text="¡Reserva Ahora!",
        cta_action=Advertisement.ActionType.BOOK_CLASS,
        cta_url="",  # Se podría poner un class_id aquí
        
        # Fechas
        start_date=timezone.now(),
        end_date=timezone.now() + timedelta(days=7),
        
        # Config
        priority=1,
        duration_seconds=5,
        is_collapsible=True,
        is_active=True,
        
        # Analytics simulados
        impressions=450,
        clicks=35
    )
    
    # Asignar imágenes si se descargaron
    if image_content:
        ad.image_desktop.save('test_ad_hero.png', image_content, save=False)
    if image_mobile_content:
        ad.image_mobile.save('test_ad_mobile.png', image_mobile_content, save=False)
    
    ad.save()
    
    print(f"\n✅ Anuncio creado exitosamente!")
    print(f"   ID: {ad.id}")
    print(f"   Título: {ad.title}")
    print(f"   Posición: {ad.get_position_display()}")
    print(f"   Tipo: {ad.get_ad_type_display()}")
    print(f"   CTA: {ad.cta_text} ({ad.get_cta_action_display()})")
    print(f"   Estado: {'✓ Activo' if ad.is_active else '✗ Inactivo'}")
    print(f"   Métricas: {ad.impressions} vistas, {ad.clicks} clicks, {ad.ctr}% CTR")
    print(f"   Válido hasta: {ad.end_date.strftime('%d/%m/%Y %H:%M')}")
    
    print(f"\n🔗 Ver en backoffice:")
    print(f"   http://127.0.0.1:8000/backoffice/marketing/advertisements/")
    print(f"   http://127.0.0.1:8000/backoffice/marketing/advertisements/{ad.id}/edit/")
    
    return ad

if __name__ == "__main__":
    print("=" * 60)
    print("🚀 Creando Anuncio Publicitario de Prueba")
    print("=" * 60)
    
    # Eliminar anuncios de prueba anteriores
    existing = Advertisement.objects.filter(title__contains="Prueba")
    if existing.exists():
        print(f"\n🗑️ Eliminando {existing.count()} anuncio(s) de prueba anterior(es)...")
        existing.delete()
    
    ad = create_test_advertisement()
    
    print("\n" + "=" * 60)
    print("✨ ¡Listo! Recarga la página del backoffice para verlo")
    print("=" * 60)
