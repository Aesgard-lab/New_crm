"""
Script de test completo para funcionalidad de devoluciones
"""
import os
import sys
import django

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'config.settings')
django.setup()

from decimal import Decimal
from django.utils import timezone
from django.contrib.auth import get_user_model
from django.contrib.contenttypes.models import ContentType
from clients.models import Client
from sales.models import Order, OrderItem, OrderPayment, OrderRefund
from finance.models import PaymentMethod
from memberships.models import MembershipPlan
from services.models import Service
from products.models import Product
from organizations.models import Gym

def run_test():
    print("=" * 60)
    print("TEST DE DEVOLUCIONES - INICIO")
    print("=" * 60)
    
    # 1. Obtener gym y usuario
    gym = Gym.objects.first()
    User = get_user_model()
    user = User.objects.filter(is_superuser=True).first()
    
    print(f"\n📍 Gym: {gym}")
    print(f"👤 User: {user}")
    
    # 2. Crear cliente demo
    client, created = Client.objects.get_or_create(
        gym=gym,
        email='demo.refund.test@test.com',
        defaults={
            'first_name': 'Demo',
            'last_name': 'Test Devolución',
            'phone_number': '600123456',
            'status': 'ACTIVE'
        }
    )
    print(f"\n👤 Cliente: {client.first_name} {client.last_name} (ID: {client.id})")
    if created:
        print("   ✅ Cliente creado nuevo")
    
    # 3. Obtener métodos de pago
    efectivo = PaymentMethod.objects.filter(gym=gym, name__icontains='efectivo').first()
    stripe_method = PaymentMethod.objects.filter(gym=gym, gateway='STRIPE').first()
    if not stripe_method:
        stripe_method = PaymentMethod.objects.filter(gym=gym, name__icontains='tarjeta').first()
    
    print(f"\n💳 Método Efectivo: {efectivo}")
    print(f"💳 Método Stripe/Tarjeta: {stripe_method}")
    
    # 4. Obtener productos para vender
    plan = MembershipPlan.objects.filter(gym=gym, is_active=True).first()
    servicio = Service.objects.filter(gym=gym).first()
    producto = Product.objects.filter(gym=gym, is_active=True).first()
    
    print(f"\n📦 Plan disponible: {plan} - {plan.base_price if plan else 0}€")
    print(f"📦 Servicio disponible: {servicio} - {servicio.base_price if servicio else 0}€")
    print(f"📦 Producto disponible: {producto} - {producto.base_price if producto else 0}€")
    
    # Obtener content types
    plan_ct = ContentType.objects.get_for_model(MembershipPlan)
    service_ct = ContentType.objects.get_for_model(Service)
    product_ct = ContentType.objects.get_for_model(Product)
    
    # ============================================
    # TICKET 1: Cuota pagada con Stripe
    # ============================================
    print("\n" + "=" * 60)
    print("TICKET 1: CUOTA PAGADA CON STRIPE")
    print("=" * 60)
    
    order1 = Order.objects.create(
        gym=gym,
        client=client,
        created_by=user,
        status='PAID',
        total_amount=Decimal('50.00'),
        total_tax=Decimal('8.68'),
        created_at=timezone.now()
    )
    
    OrderItem.objects.create(
        order=order1,
        content_type=plan_ct,
        object_id=plan.id,
        description=f"Cuota: {plan.name if plan else 'Plan Test'}",
        quantity=1,
        unit_price=Decimal('50.00'),
        tax_rate=Decimal('21.00'),
        subtotal=Decimal('50.00')
    )
    
    # Pago con Stripe (simulamos transaction_id)
    payment1 = OrderPayment.objects.create(
        order=order1,
        payment_method=stripe_method or efectivo,
        amount=Decimal('50.00'),
        gateway_used='STRIPE',
        transaction_id='pi_test_stripe_123456'  # Simulamos ID de Stripe
    )
    
    print(f"✅ Ticket #{order1.pk} creado - {order1.total_amount}€")
    print(f"   Pago: {payment1.payment_method.name} - ID: {payment1.transaction_id}")
    
    # ============================================
    # TICKET 2: Servicio pagado en efectivo
    # ============================================
    print("\n" + "=" * 60)
    print("TICKET 2: SERVICIO PAGADO EN EFECTIVO")
    print("=" * 60)
    
    order2 = Order.objects.create(
        gym=gym,
        client=client,
        created_by=user,
        status='PAID',
        total_amount=Decimal('30.00'),
        total_tax=Decimal('5.21'),
        created_at=timezone.now()
    )
    
    OrderItem.objects.create(
        order=order2,
        content_type=service_ct,
        object_id=servicio.id,
        description=f"Servicio: {servicio.name if servicio else 'Servicio Test'}",
        quantity=1,
        unit_price=Decimal('30.00'),
        tax_rate=Decimal('21.00'),
        subtotal=Decimal('30.00')
    )
    
    payment2 = OrderPayment.objects.create(
        order=order2,
        payment_method=efectivo,
        amount=Decimal('30.00'),
        gateway_used='NONE'
    )
    
    print(f"✅ Ticket #{order2.pk} creado - {order2.total_amount}€")
    print(f"   Pago: {payment2.payment_method.name}")
    
    # ============================================
    # TICKET 3: Producto pagado en efectivo
    # ============================================
    print("\n" + "=" * 60)
    print("TICKET 3: PRODUCTO PAGADO EN EFECTIVO")
    print("=" * 60)
    
    order3 = Order.objects.create(
        gym=gym,
        client=client,
        created_by=user,
        status='PAID',
        total_amount=Decimal('25.00'),
        total_tax=Decimal('4.34'),
        created_at=timezone.now()
    )
    
    OrderItem.objects.create(
        order=order3,
        content_type=product_ct,
        object_id=producto.id,
        description=f"Producto: {producto.name if producto else 'Producto Test'}",
        quantity=2,
        unit_price=Decimal('12.50'),
        tax_rate=Decimal('21.00'),
        subtotal=Decimal('25.00')
    )
    
    payment3 = OrderPayment.objects.create(
        order=order3,
        payment_method=efectivo,
        amount=Decimal('25.00'),
        gateway_used='NONE'
    )
    
    print(f"✅ Ticket #{order3.pk} creado - {order3.total_amount}€")
    print(f"   Pago: {payment3.payment_method.name}")
    
    # ============================================
    # DEVOLUCIÓN 1: Parcial del producto (con cobro negativo)
    # ============================================
    print("\n" + "=" * 60)
    print("DEVOLUCIÓN 1: PARCIAL DEL PRODUCTO (COBRO NEGATIVO)")
    print("=" * 60)
    
    refund_amount1 = Decimal('10.00')
    
    refund1 = OrderRefund.objects.create(
        order=order3,
        payment=payment3,
        amount=refund_amount1,
        reason='Test devolución parcial',
        notes='Devolución de 1 unidad del producto',
        status='COMPLETED',
        gateway='manual',
        refund_method_name=efectivo.name,
        created_by=user
    )
    
    # Actualizar total_refunded en la orden
    order3.total_refunded = refund_amount1
    order3.save()
    
    # Crear cobro negativo
    negative_order = Order.objects.create(
        gym=gym,
        client=client,
        created_by=user,
        status='PAID',
        total_amount=-refund_amount1,
        total_tax=Decimal('-1.74'),
        internal_notes=f"Devolución del Ticket #{order3.pk}"
    )
    
    OrderItem.objects.create(
        order=negative_order,
        content_type=product_ct,
        object_id=producto.id,
        description=f"Devolución: {producto.name if producto else 'Producto Test'}",
        quantity=1,
        unit_price=-refund_amount1,
        tax_rate=Decimal('21.00'),
        subtotal=-refund_amount1
    )
    
    OrderPayment.objects.create(
        order=negative_order,
        payment_method=efectivo,
        amount=-refund_amount1,
        gateway_used='NONE'
    )
    
    # Vincular el cobro negativo a la devolución
    refund1.negative_order = negative_order
    refund1.save()
    
    print(f"✅ Devolución creada: {refund1.amount}€")
    print(f"   Motivo: {refund1.reason}")
    print(f"   Notas: {refund1.notes}")
    print(f"   Método: {refund1.refund_method_name}")
    print(f"   ✅ Ticket negativo #{negative_order.pk} creado: {negative_order.total_amount}€")
    
    # ============================================
    # DEVOLUCIÓN 2: Parcial de la cuota (solo registrar, Stripe)
    # ============================================
    print("\n" + "=" * 60)
    print("DEVOLUCIÓN 2: PARCIAL DE CUOTA (SOLO REGISTRAR - STRIPE)")
    print("=" * 60)
    
    refund_amount2 = Decimal('15.00')
    
    refund2 = OrderRefund.objects.create(
        order=order1,
        payment=payment1,
        amount=refund_amount2,
        reason='Descuento aplicado posteriormente',
        notes='Cliente pidió ajuste de precio. Devolución por Stripe.',
        status='COMPLETED',
        gateway='stripe',
        gateway_refund_id='re_test_stripe_refund_789',  # Simulamos ID de refund de Stripe
        refund_method_name='Stripe',
        created_by=user
    )
    
    # Actualizar total_refunded en la orden
    order1.total_refunded = refund_amount2
    order1.save()
    
    # NO crear cobro negativo (solo registrar)
    print(f"✅ Devolución creada: {refund2.amount}€")
    print(f"   Motivo: {refund2.reason}")
    print(f"   Notas: {refund2.notes}")
    print(f"   Método: {refund2.refund_method_name}")
    print(f"   Gateway: {refund2.gateway}")
    print(f"   ID Refund Gateway: {refund2.gateway_refund_id}")
    print(f"   ⚠️ Sin ticket negativo (solo registro)")
    
    # ============================================
    # RESUMEN FINAL
    # ============================================
    print("\n" + "=" * 60)
    print("RESUMEN DEL TEST")
    print("=" * 60)
    
    print(f"\n📋 Cliente: {client.first_name} {client.last_name}")
    print(f"\n📦 TICKETS CREADOS:")
    print(f"   - Ticket #{order1.pk}: {order1.total_amount}€ (Cuota - Stripe) | Devuelto: {order1.total_refunded}€")
    print(f"   - Ticket #{order2.pk}: {order2.total_amount}€ (Servicio - Efectivo)")
    print(f"   - Ticket #{order3.pk}: {order3.total_amount}€ (Producto - Efectivo) | Devuelto: {order3.total_refunded}€")
    print(f"   - Ticket #{negative_order.pk}: {negative_order.total_amount}€ (Ticket NEGATIVO)")
    
    print(f"\n↩️ DEVOLUCIONES:")
    all_refunds = OrderRefund.objects.filter(order__client=client).order_by('-created_at')
    for r in all_refunds:
        neg_info = f" → Ticket negativo #{r.negative_order.pk}" if r.negative_order else " (solo registro)"
        print(f"   - {r.amount}€ del Ticket #{r.order.pk} via {r.refund_method_name}{neg_info}")
    
    print(f"\n💰 BALANCE:")
    total_ventas = order1.total_amount + order2.total_amount + order3.total_amount
    total_devoluciones = order1.total_refunded + order3.total_refunded
    print(f"   Total ventas: {total_ventas}€")
    print(f"   Total devuelto: {total_devoluciones}€")
    print(f"   Neto: {total_ventas - total_devoluciones}€")
    
    print("\n" + "=" * 60)
    print("✅ TEST COMPLETADO EXITOSAMENTE")
    print("=" * 60)
    
    print(f"\n🔗 IDs para verificar en el admin/dashboard:")
    print(f"   Cliente ID: {client.id}")
    print(f"   Order IDs: {order1.id}, {order2.id}, {order3.id}, {negative_order.id}")
    print(f"   Refund IDs: {refund1.id}, {refund2.id}")
    
    return {
        'client': client,
        'orders': [order1, order2, order3, negative_order],
        'refunds': [refund1, refund2]
    }

if __name__ == '__main__':
    run_test()
