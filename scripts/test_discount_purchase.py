"""
Test completo: Crear cliente, crear descuento para producto y realizar compra

Este script:
1. Crea un cliente de prueba
2. Crea un descuento para productos
3. Simula una compra aplicando el descuento
"""

import os
import django

os.environ.setdefault("DJANGO_SETTINGS_MODULE", "config.settings")
django.setup()

from django.contrib.auth import get_user_model
from django.utils import timezone
from datetime import timedelta
from decimal import Decimal

from clients.models import Client
from discounts.models import Discount, DiscountUsage
from products.models import Product, ProductCategory
from sales.models import Order, OrderItem
from organizations.models import Gym, Franchise
from django.contrib.contenttypes.models import ContentType

User = get_user_model()

def create_test_client(gym):
    """Crea un cliente de prueba"""
    print("\n📝 Creando cliente de prueba...")
    
    # Buscar o crear usuario
    email = "test_discount_client@test.com"
    user, created = User.objects.get_or_create(
        email=email,
        defaults={
            'first_name': 'Cliente',
            'last_name': 'Test Descuento'
        }
    )
    
    if created:
        user.set_password('test1234')
        user.save()
        print(f"✅ Usuario creado: {user.email}")
    else:
        print(f"ℹ️  Usuario existente: {user.email}")
    
    # Buscar o crear cliente
    client, created = Client.objects.get_or_create(
        user=user,
        gym=gym,
        defaults={
            'first_name': 'Cliente',
            'last_name': 'Test Descuento',
            'phone_number': '+34666777888',
            'birth_date': '1990-01-01',
            'status': Client.Status.ACTIVE,
        }
    )
    
    if created:
        print(f"✅ Cliente creado: {client}")
    else:
        print(f"ℹ️  Cliente existente: {client}")
    
    return client


def create_test_discount(gym, product):
    """Crea un descuento para productos"""
    print("\n🎁 Creando descuento para productos...")
    
    discount, created = Discount.objects.get_or_create(
        gym=gym,
        code='TEST20',
        defaults={
            'name': 'Descuento Test 20%',
            'discount_type': Discount.DiscountType.PERCENTAGE,
            'value': Decimal('20.00'),
            'is_active': True,
            'valid_from': timezone.now(),
            'valid_until': timezone.now() + timedelta(days=30),
            'max_uses_total': 100,
            'max_uses_per_client': 10,  # Permitir múltiples usos
            'current_uses': 0,
            'applies_to': Discount.AppliesTo.SPECIFIC_ITEMS,
        }
    )
    
    if created:
        # Configurar productos aplicables
        discount.specific_products.add(product)
        print(f"✅ Descuento creado: {discount.code} - {discount.name}")
        print(f"   Tipo: {discount.get_discount_type_display()}")
        print(f"   Valor: {discount.value}%")
        print(f"   Aplicable a: {product.name}")
    else:
        print(f"ℹ️  Descuento existente: {discount.code}")
        # Actualizar max_uses_per_client si es diferente
        if discount.max_uses_per_client != 10:
            discount.max_uses_per_client = 10
            discount.save()
            print(f"   ✏️  Actualizado: max_uses_per_client = 10")
        if not discount.specific_products.filter(id=product.id).exists():
            discount.specific_products.add(product)
            print(f"   ➕ Producto añadido al descuento")
    
    return discount


def create_test_product(gym):
    """Crea o busca un producto de prueba"""
    print("\n📦 Preparando producto...")
    
    # Buscar o crear categoría
    category, created = ProductCategory.objects.get_or_create(
        gym=gym,
        name='Test Category'
    )
    
    if created:
        print(f"✅ Categoría creada: {category.name}")
    
    # Buscar o crear producto
    product, created = Product.objects.get_or_create(
        gym=gym,
        name='Producto Test para Descuento',
        defaults={
            'category': category,
            'base_price': Decimal('50.00'),
            'stock_quantity': 100,
            'is_active': True,
            'description': 'Producto de prueba para test de descuento',
        }
    )
    
    if created:
        print(f"✅ Producto creado: {product.name}")
        print(f"   Precio: €{product.base_price}")
        print(f"   Stock: {product.stock_quantity}")
    else:
        print(f"ℹ️  Producto existente: {product.name}")
    
    return product


def simulate_purchase_with_discount(gym, client, product, discount):
    """Simula una compra con descuento aplicado"""
    print("\n💳 Simulando compra con descuento...")
    
    # Calcular precio con descuento
    original_price = product.base_price
    if discount.discount_type == Discount.DiscountType.PERCENTAGE:
        discount_amount = original_price * (discount.value / Decimal('100'))
    else:
        discount_amount = discount.value
    
    final_price = original_price - discount_amount
    
    print(f"\n💰 Detalles de la compra:")
    print(f"   Producto: {product.name}")
    print(f"   Precio original: €{original_price}")
    print(f"   Descuento ({discount.code}): -{discount.value}%")
    print(f"   Descuento en €: -€{discount_amount}")
    print(f"   Precio final: €{final_price}")
    
    # Crear venta
    order = Order.objects.create(
        gym=gym,
        client=client,
        created_by=client.user,
        total_amount=final_price,
        total_discount=discount_amount,
        total_base=final_price,
        total_tax=Decimal('0.00'),
        status='PAID',
        internal_notes=f'Test con descuento {discount.code}'
    )
    
    # Crear item de venta
    product_ct = ContentType.objects.get_for_model(Product)
    OrderItem.objects.create(
        order=order,
        content_type=product_ct,
        object_id=product.id,
        description=product.name,
        quantity=1,
        unit_price=original_price,
        discount_amount=discount_amount,
        tax_rate=Decimal('0.00'),
        subtotal=final_price
    )
    
    # Registrar uso del descuento
    DiscountUsage.objects.create(
        discount=discount,
        client=client,
        order=order,
        discount_name=discount.name,
        discount_type=discount.discount_type,
        discount_value=discount.value,
        subtotal=original_price,
        discount_amount=discount_amount,
        final_amount=final_price,
        code_used=discount.code
    )
    
    # Actualizar contador de uso del descuento
    discount.current_uses += 1
    discount.save()
    
    # Actualizar stock
    product.stock_quantity -= 1
    product.save()
    
    print(f"\n✅ Venta completada!")
    print(f"   ID Venta: {order.id}")
    print(f"   Ahorro para el cliente: €{discount_amount}")
    print(f"   Stock restante: {product.stock_quantity}")
    print(f"   Usos del descuento: {discount.current_uses}")
    
    return order


def main():
    print("=" * 60)
    print("🧪 TEST: Cliente compra producto con descuento")
    print("=" * 60)
    
    # Obtener gimnasio
    gym = Gym.objects.first()
    if not gym:
        print("❌ No se encontró ningún gimnasio. Crea uno primero.")
        return
    
    print(f"\n🏋️ Gimnasio: {gym.name}")
    
    # 1. Crear cliente
    client = create_test_client(gym)
    
    # 2. Crear/obtener producto
    product = create_test_product(gym)
    
    # 3. Crear descuento
    discount = create_test_discount(gym, product)
    
    # 4. Validar que el descuento puede aplicarse
    print("\n🔍 Validando descuento...")
    can_use = discount.can_be_used_by_client(client)
    if can_use:
        print(f"✅ Descuento puede ser usado por el cliente")
    else:
        print(f"❌ El descuento no puede ser usado por este cliente")
        return
    
    # 5. Simular compra
    order = simulate_purchase_with_discount(gym, client, product, discount)
    
    # Resumen final
    print("\n" + "=" * 60)
    print("📊 RESUMEN DEL TEST")
    print("=" * 60)
    print(f"Cliente: {client.user.get_full_name()}")
    print(f"Email: {client.user.email}")
    print(f"Producto: {product.name}")
    print(f"Descuento: {discount.code} ({discount.value}%)")
    print(f"Venta ID: {order.id}")
    print(f"Total pagado: €{order.total_amount}")
    print(f"Ahorro: €{order.total_discount}")
    print("\n✅ Test completado exitosamente!")
    print("=" * 60)


if __name__ == "__main__":
    main()
