"""
Script para probar los endpoints de la API de anuncios.
Simula llamadas desde la app del cliente.
"""

import os
import django
import sys

# Setup Django
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'config.settings')
django.setup()

from django.test import RequestFactory, Client as TestClient
from django.contrib.auth import get_user_model
from clients.models import Client
from marketing.models import Advertisement
from marketing import api
import json

User = get_user_model()

def test_api_endpoints():
    """Prueba los endpoints de la API de anuncios"""
    
    print("=" * 60)
    print("🧪 PROBANDO ENDPOINTS DE API DE ANUNCIOS")
    print("=" * 60)
    
    # 1. Buscar un cliente de prueba
    print("\n1️⃣ Buscando cliente de prueba...")
    try:
        # Buscar un cliente que tenga usuario asociado
        client = Client.objects.filter(user__isnull=False).first()
        if not client:
            print("❌ No hay clientes con usuario asociado")
            print("   Crea uno desde el panel de administración")
            return
        
        print(f"✅ Cliente encontrado: {client.first_name} {client.last_name}")
        print(f"   Email: {client.email}")
        print(f"   Gym: {client.gym.name}")
        print(f"   User ID: {client.user.id}")
    except Exception as e:
        print(f"❌ Error: {e}")
        return
    
    # 2. Crear cliente de prueba HTTP
    print("\n2️⃣ Creando cliente HTTP de prueba...")
    test_client = TestClient()
    
    # Login con el usuario del cliente (intentar con email y username)
    username = getattr(client.user, 'username', client.user.email)
    login_success = test_client.login(username=username, password='admin123')
    if not login_success:
        print("⚠️  No se pudo hacer login automático")
        print("   Los endpoints usan RequestFactory con user ya autenticado")
    
    # 3. Probar GET /api/advertisements/active/
    print("\n3️⃣ Probando GET /marketing/api/advertisements/active/")
    print("   (Obteniendo anuncios activos)")
    try:
        factory = RequestFactory()
        request = factory.get('/marketing/api/advertisements/active/')
        request.user = client.user
        request.gym = client.gym
        
        response = api.api_get_active_advertisements(request)
        data = json.loads(response.content)
        
        print(f"\n   📊 Respuesta:")
        print(f"   - Status Code: {response.status_code}")
        print(f"   - Total anuncios: {data.get('count', 0)}")
        
        if data.get('results'):
            for ad in data['results']:
                print(f"\n   📢 Anuncio ID {ad['id']}:")
                print(f"      Título: {ad['title']}")
                print(f"      Posición: {ad['position']}")
                print(f"      Tipo: {ad['ad_type']}")
                if ad.get('cta'):
                    print(f"      CTA: {ad['cta']['text']} ({ad['cta']['action']})")
        else:
            print("   ⚠️  No hay anuncios activos")
    except Exception as e:
        print(f"   ❌ Error: {e}")
        import traceback
        traceback.print_exc()
    
    # 4. Probar GET con filtro de posición
    print("\n4️⃣ Probando GET con filtro ?position=HERO_CAROUSEL")
    try:
        request = factory.get('/marketing/api/advertisements/active/?position=HERO_CAROUSEL')
        request.user = client.user
        request.gym = client.gym
        
        response = api.api_get_active_advertisements(request)
        data = json.loads(response.content)
        
        print(f"   - Anuncios tipo Hero Carousel: {data.get('count', 0)}")
    except Exception as e:
        print(f"   ❌ Error: {e}")
    
    # 5. Probar POST impression (si hay anuncios)
    print("\n5️⃣ Probando POST /api/advertisements/{id}/impression/")
    try:
        ad = Advertisement.objects.filter(is_active=True).first()
        if ad:
            impressions_before = ad.impressions
            
            request = factory.post(f'/marketing/api/advertisements/{ad.id}/impression/')
            request.user = client.user
            request.gym = client.gym
            
            response = api.api_track_advertisement_impression(request, ad.id)
            data = json.loads(response.content)
            
            print(f"   - Anuncio ID: {ad.id}")
            print(f"   - Impresiones antes: {impressions_before}")
            print(f"   - Respuesta: {data.get('message')}")
            
            # Refrescar el anuncio para ver el contador actualizado
            ad.refresh_from_db()
            print(f"   - Impresiones después: {ad.impressions}")
            print(f"   ✅ Impresión registrada correctamente")
        else:
            print("   ⚠️  No hay anuncios activos para probar")
    except Exception as e:
        print(f"   ❌ Error: {e}")
        import traceback
        traceback.print_exc()
    
    # 6. Probar POST click (si hay anuncios)
    print("\n6️⃣ Probando POST /api/advertisements/{id}/click/")
    try:
        ad = Advertisement.objects.filter(is_active=True, cta_text__isnull=False).first()
        if ad:
            clicks_before = ad.clicks
            
            request = factory.post(
                f'/marketing/api/advertisements/{ad.id}/click/',
                data=json.dumps({'action': ad.cta_action}),
                content_type='application/json'
            )
            request.user = client.user
            request.gym = client.gym
            
            response = api.api_track_advertisement_click(request, ad.id)
            data = json.loads(response.content)
            
            print(f"   - Anuncio ID: {ad.id}")
            print(f"   - Clicks antes: {clicks_before}")
            print(f"   - Acción CTA: {ad.cta_action}")
            print(f"   - Respuesta: {data.get('message')}")
            print(f"   - Redirigir a: {data.get('redirect_to')}")
            
            # Refrescar el anuncio para ver el contador actualizado
            ad.refresh_from_db()
            print(f"   - Clicks después: {ad.clicks}")
            print(f"   - CTR actual: {ad.ctr:.2f}%")
            print(f"   ✅ Click registrado correctamente")
        else:
            print("   ⚠️  No hay anuncios con CTA para probar")
    except Exception as e:
        print(f"   ❌ Error: {e}")
        import traceback
        traceback.print_exc()
    
    # 7. Probar GET positions
    print("\n7️⃣ Probando GET /api/advertisements/positions/")
    try:
        request = factory.get('/marketing/api/advertisements/positions/')
        request.user = client.user
        
        response = api.api_get_advertisement_positions(request)
        data = json.loads(response.content)
        
        print(f"   - Posiciones disponibles: {len(data.get('positions', []))}")
        for pos in data.get('positions', []):
            print(f"      • {pos['value']}: {pos['label']}")
    except Exception as e:
        print(f"   ❌ Error: {e}")
    
    print("\n" + "=" * 60)
    print("✅ PRUEBA DE API COMPLETADA")
    print("=" * 60)
    print("\n📚 Endpoints disponibles:")
    print("   GET  /marketing/api/advertisements/active/")
    print("        ?position=HERO_CAROUSEL")
    print("   POST /marketing/api/advertisements/{id}/impression/")
    print("   POST /marketing/api/advertisements/{id}/click/")
    print("   GET  /marketing/api/advertisements/positions/")
    print("\n💡 Úsalos desde tu app del cliente (React/Vue/Flutter)")
    print("=" * 60)


if __name__ == '__main__':
    test_api_endpoints()
