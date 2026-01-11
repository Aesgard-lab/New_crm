import os
import django
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'config.settings')
django.setup()

from products.models import Product, ProductCategory
from services.models import Service, ServiceCategory
from organizations.models import Gym
from finance.models import TaxRate
from decimal import Decimal

gym = Gym.objects.first()

if gym:
    print(f"Adding data for gym: {gym.name}")
    
    # Tax
    tax, _ = TaxRate.objects.get_or_create(gym=gym, name="IVA 21%", defaults={'rate_percent': 21.00})
    
    # Product Category
    p_cat, _ = ProductCategory.objects.get_or_create(gym=gym, name="Nutrición")
    
    # Products
    if not Product.objects.filter(gym=gym).exists():
        Product.objects.create(gym=gym, name="Proteína Whey 1kg (Demo)", base_price=Decimal("45.00"), tax_rate=tax, category=p_cat, is_active=True)
        Product.objects.create(gym=gym, name="Barrita Energética (Demo)", base_price=Decimal("2.50"), tax_rate=tax, category=p_cat, is_active=True)
        print("Created products.")
    else:
        print("Products already exist.")

    # Service Category
    s_cat, _ = ServiceCategory.objects.get_or_create(gym=gym, name="Generales")

    # Services
    if not Service.objects.filter(gym=gym).exists():
        Service.objects.create(gym=gym, name="Pase Diario (Demo)", base_price=Decimal("10.00"), tax_rate=tax, category=s_cat, is_active=True)
        Service.objects.create(gym=gym, name="Clase Suelta (Demo)", base_price=Decimal("15.00"), tax_rate=tax, category=s_cat, is_active=True)
        print("Created services.")
    else:
        print("Services already exist.")
else:
    print("No gym found")
