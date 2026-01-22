"""
Script para configurar el portal público y métodos de pago
"""

import os
import django

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'config.settings')
django.setup()

from organizations.models import Gym, PublicPortalSettings
from finance.models import PaymentMethod

def setup_portal_access():
    """Configura el acceso al portal público para todos los gimnasios"""
    
    gyms = Gym.objects.all()
    
    for gym in gyms:
        # Crear o actualizar settings del portal público
        settings, created = PublicPortalSettings.objects.get_or_create(
            gym=gym,
            defaults={
                'public_slug': gym.slug if hasattr(gym, 'slug') and gym.slug else gym.name.lower().replace(' ', '-'),
                'public_portal_enabled': True,
                'allow_self_registration': True,
                'require_staff_approval': False,
                'require_email_verification': False,
                'show_schedule': True,
                'show_pricing': True,
                'show_services': True,
                'show_shop': True,
                'allow_embedding': True,
                'booking_requires_login': True,
                'booking_requires_payment': False,
            }
        )
        
        if not created:
            # Actualizar settings existentes
            settings.public_portal_enabled = True
            settings.show_schedule = True
            settings.show_pricing = True
            settings.show_services = True
            settings.show_shop = True
            settings.save()
        
        print(f"✓ Portal configurado para {gym.name}")
        print(f"  URL: /public/gym/{settings.public_slug}/")
        
        # Crear métodos de pago si no existen
        if not PaymentMethod.objects.filter(gym=gym).exists():
            # Efectivo
            PaymentMethod.objects.create(
                gym=gym,
                name="Efectivo",
                description="Pago en efectivo en recepción",
                is_cash=True,
                is_active=True,
                available_for_online=False,
                display_order=1,
                gateway='NONE'
            )
            
            # Tarjeta (TPV físico)
            PaymentMethod.objects.create(
                gym=gym,
                name="Tarjeta (TPV)",
                description="Pago con tarjeta en recepción",
                is_cash=False,
                is_active=True,
                available_for_online=False,
                display_order=2,
                gateway='NONE'
            )
            
            # Transferencia
            PaymentMethod.objects.create(
                gym=gym,
                name="Transferencia Bancaria",
                description="Transferencia a cuenta bancaria",
                is_cash=False,
                is_active=True,
                available_for_online=True,
                display_order=3,
                gateway='NONE'
            )
            
            # Stripe (online)
            PaymentMethod.objects.create(
                gym=gym,
                name="Tarjeta Online (Stripe)",
                description="Pago seguro con tarjeta",
                is_cash=False,
                is_active=False,  # Desactivado por defecto hasta configurar
                available_for_online=True,
                display_order=4,
                gateway='STRIPE'
            )
            
            # Redsys (online)
            PaymentMethod.objects.create(
                gym=gym,
                name="Tarjeta Online (Redsys)",
                description="Pago seguro con tarjeta",
                is_cash=False,
                is_active=False,  # Desactivado por defecto hasta configurar
                available_for_online=True,
                display_order=5,
                gateway='REDSYS'
            )
            
            print(f"✓ Métodos de pago creados para {gym.name}")
        else:
            # Actualizar métodos existentes para añadir campos nuevos
            for method in PaymentMethod.objects.filter(gym=gym):
                if not hasattr(method, 'available_for_online') or method.available_for_online is None:
                    # Configurar disponibilidad online según tipo
                    if method.is_cash:
                        method.available_for_online = False
                    else:
                        method.available_for_online = True
                
                if not hasattr(method, 'gateway') or not method.gateway:
                    method.gateway = 'NONE'
                
                method.save()
            
            print(f"✓ Métodos de pago actualizados para {gym.name}")
        
        print()

if __name__ == '__main__':
    print("=" * 60)
    print("Configurando Portal Público")
    print("=" * 60)
    print()
    
    setup_portal_access()
    
    print("=" * 60)
    print("✅ Configuración completada")
    print("=" * 60)
    print()
    print("Próximos pasos:")
    print("1. Accede al admin de Django")
    print("2. Configura las actividades con 'Visible Online'")
    print("3. Configura los planes con 'Visible Online'")
    print("4. Configura campos personalizados con 'Mostrar en Registro'")
    print()
    print("URLs del portal:")
    for settings in PublicPortalSettings.objects.filter(public_portal_enabled=True):
        print(f"  {settings.gym.name}: http://localhost:8000/public/gym/{settings.public_slug}/")
