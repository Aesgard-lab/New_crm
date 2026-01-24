"""
Script para marcar servicios, productos y planes como visibles online (is_visible_online=True)
para poblar la tienda del portal.
"""
import os
import django

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'config.settings')
django.setup()

from services.models import Service
from products.models import Product
from memberships.models import MembershipPlan
from organizations.models import Gym

def populate_shop():
    """Marcar algunos items como visibles en la tienda online"""
    
    gym = Gym.objects.first()
    if not gym:
        print("❌ No se encontró ningún gimnasio")
        return
    
    print(f"🏋️  Configurando tienda para: {gym.name}\n")
    
    # Servicios
    services = Service.objects.filter(gym=gym, is_active=True)[:3]
    count_services = 0
    for service in services:
        service.is_visible_online = True
        service.save(update_fields=['is_visible_online'])
        count_services += 1
        print(f"✅ Servicio visible: {service.name} - {service.final_price}€")
    
    # Productos
    products = Product.objects.filter(gym=gym, is_active=True)[:3]
    count_products = 0
    for product in products:
        product.is_visible_online = True
        product.save(update_fields=['is_visible_online'])
        count_products += 1
        print(f"✅ Producto visible: {product.name} - {product.final_price}€")
    
    # Planes de membresía
    plans = MembershipPlan.objects.filter(gym=gym, is_active=True)[:3]
    count_plans = 0
    for plan in plans:
        plan.is_visible_online = True
        plan.save(update_fields=['is_visible_online'])
        count_plans += 1
        print(f"✅ Plan visible: {plan.name} - {plan.final_price}€")
    
    print(f"\n📊 Resumen:")
    print(f"   • {count_services} servicios visibles")
    print(f"   • {count_products} productos visibles")
    print(f"   • {count_plans} planes visibles")
    print(f"\n🔗 Ver tienda: http://localhost:8000/portal/shop/")

if __name__ == '__main__':
    populate_shop()
