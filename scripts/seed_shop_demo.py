
import os
import sys
import django
from decimal import Decimal

# Setup Django
sys.path.append(os.getcwd())
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'config.settings')
django.setup()

from organizations.models import Gym
from products.models import Product, ProductCategory
from services.models import Service, ServiceCategory
from memberships.models import MembershipPlan
from products.models import TaxRate

def seed_shop():
    gym = Gym.objects.first()
    if not gym:
        print("No gym found")
        return

    print(f"Seeding shop for: {gym.name}")

    # 1. Tax Rate
    tax, _ = TaxRate.objects.get_or_create(
        gym=gym,
        name="IVA General",
        defaults={'rate_percent': 21.00}
    )

    # 2. Products
    cat_prod, _ = ProductCategory.objects.get_or_create(gym=gym, name="Suplementos")
    
    p1, created = Product.objects.get_or_create(
        gym=gym,
        name="Proteína Whey 1kg - Vainilla",
        defaults={
            'description': 'Proteína de suero de alta calidad. Sulanoricio de vainilla.',
            'base_price': Decimal("35.00"),
            'category': cat_prod,
            'tax_rate': tax,
            'stock_quantity': 50,
            'track_stock': True,
            'is_active': True,
            'is_visible_online': True
        }
    )
    if created: print(f"Created Product: {p1.name}")

    p2, created = Product.objects.get_or_create(
        gym=gym,
        name="Camiseta Gym Brand",
        defaults={
            'description': 'Camiseta técnica transpirable con el logo del gimnasio.',
            'base_price': Decimal("15.00"),
            'category': cat_prod, # Reuse for simplicity or create Apparel
            'tax_rate': tax,
            'is_active': True,
            'is_visible_online': True
        }
    )
    if created: print(f"Created Product: {p2.name}")

    # 3. Services
    cat_serv, _ = ServiceCategory.objects.get_or_create(gym=gym, name="Entrenamiento")
    
    s1, created = Service.objects.get_or_create(
        gym=gym,
        name="Sesión Personal (1h)",
        defaults={
            'description': 'Entrenamiento personalizado unidireccional con un coach experto.',
            'base_price': Decimal("40.00"),
            'duration': 60,
            'category': cat_serv,
            'tax_rate': tax,
            'color': '#3B82F6',
            'is_active': True,
            'is_visible_online': True
        }
    )
    if created: print(f"Created Service: {s1.name}")

    s2, created = Service.objects.get_or_create(
        gym=gym,
        name="Consulta Nutricional",
        defaults={
            'description': 'Análisis corporal y plan de dieta personalizado.',
            'base_price': Decimal("30.00"),
            'duration': 45,
            'category': cat_serv,
            'tax_rate': tax,
            'color': '#10B981',
            'is_active': True,
            'is_visible_online': True
        }
    )
    if created: print(f"Created Service: {s2.name}")

    # 4. Membership Plans
    mp1, created = MembershipPlan.objects.get_or_create(
        gym=gym,
        name="Plan Mensual Básico",
        defaults={
            'description': 'Acceso ilimitado a la sala de pesas. Sin clases incluidas.',
            'price': Decimal("29.99"),
            'duration_type': 'MONTHLY',
            'duration_months': 1,
            'access_type': 'UNLIMITED',
            'is_active': True
        }
    )
    if created: print(f"Created Plan: {mp1.name}")

    mp2, created = MembershipPlan.objects.get_or_create(
        gym=gym,
        name="Plan Premium Trimestral",
        defaults={
            'description': 'Acceso total + Clases ilimitadas + 1 sesión de PT al mes.',
            'price': Decimal("85.00"),
            'duration_type': 'QUARTERLY',
            'duration_months': 3,
            'access_type': 'UNLIMITED',
            'is_active': True
        }
    )
    if created: print(f"Created Plan: {mp2.name}")

if __name__ == '__main__':
    seed_shop()
