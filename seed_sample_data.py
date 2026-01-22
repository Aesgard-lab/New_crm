"""
Script para crear datos de prueba realistas:
- Ventas de membresías/cuotas
- Ventas de servicios
- Ventas de productos
- Reservas de clases
- Reservas de servicios
"""
import os
import sys
import django
import random
from datetime import datetime, timedelta
from decimal import Decimal

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'config.settings')
django.setup()

from django.utils import timezone
from django.db import transaction
from django.contrib.contenttypes.models import ContentType
from clients.models import Client, ClientMembership
from organizations.models import Gym
from activities.models import Activity, ActivitySession, Room
from services.models import Service, ServiceAppointment
from products.models import Product
from memberships.models import MembershipPlan
from sales.models import Order, OrderItem, OrderPayment
from finance.models import PaymentMethod
from staff.models import StaffProfile
from accounts.models import User

def create_sample_data(gym_id=1):
    """Crear datos de ejemplo para un gimnasio"""
    
    gym = Gym.objects.get(id=gym_id)
    clients = list(Client.objects.filter(gym=gym, status='ACTIVE'))
    
    if not clients:
        print("No hay clientes activos. Creando algunos...")
        clients = create_sample_clients(gym)
    
    print(f"\n📊 Creando datos para {gym.name} con {len(clients)} clientes...")
    
    # Obtener recursos
    activities = list(Activity.objects.filter(gym=gym))
    services = list(Service.objects.filter(gym=gym))
    products = list(Product.objects.filter(gym=gym))
    plans = list(MembershipPlan.objects.filter(gym=gym, is_active=True))
    
    # Obtener método de pago por defecto
    payment_method = PaymentMethod.objects.filter(gym=gym).first()
    if not payment_method:
        payment_method = PaymentMethod.objects.create(
            gym=gym,
            name="Efectivo",
            method_type="CASH",
            is_active=True
        )
    
    # Usuario admin para las órdenes
    admin_user = User.objects.filter(is_superuser=True).first()
    
    with transaction.atomic():
        # 1. Crear membresías para clientes
        if plans:
            print("\n💳 Creando membresías...")
            create_memberships(clients, plans, gym, payment_method, admin_user)
        
        # 2. Crear ventas de productos
        if products:
            print("\n🛒 Creando ventas de productos...")
            create_product_sales(clients, products, gym, payment_method, admin_user)
        
        # 3. Crear ventas de servicios
        if services:
            print("\n💆 Creando reservas y ventas de servicios...")
            create_service_sales(clients, services, gym, payment_method, admin_user)
        
        # 4. Crear sesiones de clases y reservas
        if activities:
            print("\n🏋️ Creando sesiones de clases y reservas...")
            create_class_sessions_and_bookings(clients, activities, gym)
    
    print("\n✅ Datos de ejemplo creados exitosamente!")
    
    # Limpiar caché
    from django.core.cache import cache
    cache.clear()
    print("🗑️ Caché limpiado")


def create_sample_clients(gym):
    """Crear clientes de prueba si no existen"""
    names = [
        ("Carlos", "García"),
        ("María", "López"),
        ("Pedro", "Martínez"),
        ("Ana", "Rodríguez"),
        ("Luis", "Fernández"),
        ("Laura", "Sánchez"),
        ("Diego", "González"),
        ("Elena", "Díaz"),
    ]
    
    clients = []
    for first, last in names:
        email = f"{first.lower()}.{last.lower()}@ejemplo.com"
        client, created = Client.objects.get_or_create(
            gym=gym,
            email=email,
            defaults={
                'first_name': first,
                'last_name': last,
                'phone': f"+34 6{random.randint(10000000, 99999999)}",
                'status': 'ACTIVE'
            }
        )
        clients.append(client)
        if created:
            print(f"  Creado cliente: {first} {last}")
    
    return clients


def create_memberships(clients, plans, gym, payment_method, admin_user):
    """Crear membresías con historial de pagos"""
    
    today = timezone.now().date()
    plan_ct = ContentType.objects.get_for_model(MembershipPlan)
    
    for i, client in enumerate(clients[:10]):  # Limitar a 10 clientes
        plan = random.choice(plans)
        
        # Fecha de inicio aleatoria en los últimos 6 meses
        months_ago = random.randint(1, 6)
        start_date = today - timedelta(days=30 * months_ago)
        
        # Duración según el plan
        if plan.is_recurring:
            end_date = today + timedelta(days=30)  # Activa
        else:
            end_date = start_date + timedelta(days=plan.pack_validity_days or 30)
        
        # Verificar si ya tiene membresía con ese nombre
        existing = ClientMembership.objects.filter(client=client, name=plan.name).exists()
        if existing:
            continue
            
        # Crear membresía (ClientMembership copia datos del plan)
        membership = ClientMembership.objects.create(
            client=client,
            name=plan.name,
            start_date=start_date,
            end_date=end_date,
            price=plan.base_price,
            status='ACTIVE' if end_date >= today else 'EXPIRED',
            is_recurring=plan.is_recurring,
            current_period_start=start_date,
            current_period_end=end_date,
            next_billing_date=end_date if plan.is_recurring else None,
            sessions_total=plan.pack_sessions if hasattr(plan, 'pack_sessions') else None,
            sessions_used=random.randint(0, 5)
        )
        
        # Crear orden de pago por cada mes
        current_month = start_date.replace(day=1)
        while current_month <= today:
            order_date = timezone.make_aware(
                datetime.combine(current_month, datetime.min.time())
            ) + timedelta(days=random.randint(1, 5))
            
            subtotal = plan.base_price
            tax = subtotal * Decimal('0.21')
            total = subtotal + tax
            
            order = Order.objects.create(
                gym=gym,
                client=client,
                status='PAID',
                total_base=subtotal,
                total_tax=tax,
                total_amount=total,
                created_by=admin_user,
                created_at=order_date
            )
            # Actualizar created_at manualmente
            Order.objects.filter(pk=order.pk).update(created_at=order_date)
            
            OrderItem.objects.create(
                order=order,
                content_type=plan_ct,
                object_id=plan.id,
                description=f"Cuota {plan.name}",
                quantity=1,
                unit_price=plan.base_price,
                tax_rate=Decimal('21.00'),
                subtotal=total
            )
            
            OrderPayment.objects.create(
                order=order,
                payment_method=payment_method,
                amount=total
            )
            
            current_month = (current_month + timedelta(days=32)).replace(day=1)
        
        print(f"  ✓ Membresía para {client.first_name}: {plan.name}")


def create_product_sales(clients, products, gym, payment_method, admin_user):
    """Crear ventas de productos distribuidas en los últimos meses"""
    
    today = timezone.now()
    product_ct = ContentType.objects.get_for_model(Product)
    
    # Crear entre 30-50 ventas de productos
    for _ in range(random.randint(30, 50)):
        client = random.choice(clients)
        product = random.choice(products)
        quantity = random.randint(1, 3)
        
        # Fecha aleatoria en los últimos 3 meses
        days_ago = random.randint(1, 90)
        order_date = today - timedelta(days=days_ago)
        
        subtotal = product.base_price * quantity
        tax = subtotal * Decimal('0.21')
        total = subtotal + tax
        
        order = Order.objects.create(
            gym=gym,
            client=client,
            status='PAID',
            total_base=subtotal,
            total_tax=tax,
            total_amount=total,
            created_by=admin_user
        )
        # Actualizar created_at manualmente
        Order.objects.filter(pk=order.pk).update(created_at=order_date)
        
        OrderItem.objects.create(
            order=order,
            content_type=product_ct,
            object_id=product.id,
            description=product.name,
            quantity=quantity,
            unit_price=product.base_price,
            tax_rate=Decimal('21.00'),
            subtotal=total
        )
        
        OrderPayment.objects.create(
            order=order,
            payment_method=payment_method,
            amount=total
        )
    
    print(f"  ✓ Creadas ventas de productos")


def create_service_sales(clients, services, gym, payment_method, admin_user):
    """Crear reservas de servicios con ventas"""
    
    today = timezone.now()
    staff = StaffProfile.objects.filter(gym=gym).first()
    service_ct = ContentType.objects.get_for_model(Service)
    
    # Crear entre 20-40 reservas de servicios
    for _ in range(random.randint(20, 40)):
        client = random.choice(clients)
        service = random.choice(services)
        
        # Fecha aleatoria: algunas pasadas, algunas futuras
        days_offset = random.randint(-60, 14)
        appointment_date = today + timedelta(days=days_offset)
        
        # Hora aleatoria de 9am a 7pm
        hour = random.randint(9, 19)
        start_time = appointment_date.replace(hour=hour, minute=0, second=0, microsecond=0)
        end_time = start_time + timedelta(minutes=service.duration)
        
        status = 'COMPLETED' if days_offset < 0 else 'CONFIRMED'
        
        # Crear cita
        appointment = ServiceAppointment.objects.create(
            gym=gym,
            service=service,
            client=client,
            staff=staff,
            start_datetime=start_time,
            end_datetime=end_time,
            status=status,
            notes=f"Cita de prueba para {service.name}"
        )
        
        # Crear venta solo si está completada
        if status == 'COMPLETED':
            subtotal = service.base_price
            tax = subtotal * Decimal('0.21')
            total = subtotal + tax
            
            order = Order.objects.create(
                gym=gym,
                client=client,
                status='PAID',
                total_base=subtotal,
                total_tax=tax,
                total_amount=total,
                created_by=admin_user
            )
            # Actualizar created_at manualmente
            Order.objects.filter(pk=order.pk).update(created_at=start_time)
            
            # Vincular orden a la cita
            appointment.order = order
            appointment.save()
            
            OrderItem.objects.create(
                order=order,
                content_type=service_ct,
                object_id=service.id,
                description=service.name,
                quantity=1,
                unit_price=service.base_price,
                tax_rate=Decimal('21.00'),
                subtotal=total
            )
            
            OrderPayment.objects.create(
                order=order,
                payment_method=payment_method,
                amount=total
            )
    
    print(f"  ✓ Creadas reservas de servicios")


def create_class_sessions_and_bookings(clients, activities, gym):
    """Crear sesiones de clases y reservas"""
    
    today = timezone.now()
    staff = StaffProfile.objects.filter(gym=gym).first()
    
    # Obtener sala si existe
    room = Room.objects.filter(gym=gym).first()
    
    # Crear sesiones para los últimos 30 días y próximos 14 días
    for activity in activities:
        # 3-5 sesiones por semana por actividad
        for week_offset in range(-4, 3):  # 4 semanas atrás, 2 adelante
            for _ in range(random.randint(3, 5)):
                # Día aleatorio de la semana
                day_offset = week_offset * 7 + random.randint(0, 6)
                session_date = today + timedelta(days=day_offset)
                
                # Hora aleatoria
                hour = random.choice([9, 10, 11, 17, 18, 19])
                start_time = session_date.replace(hour=hour, minute=0, second=0, microsecond=0)
                end_time = start_time + timedelta(minutes=activity.duration)
                
                # Crear sesión
                session = ActivitySession.objects.create(
                    gym=gym,
                    activity=activity,
                    room=room,
                    staff=staff,
                    start_datetime=start_time,
                    end_datetime=end_time,
                    max_capacity=activity.base_capacity,
                    status='COMPLETED' if day_offset < 0 else 'SCHEDULED'
                )
                
                # Agregar asistentes (60-100% de capacidad)
                num_attendees = random.randint(
                    int(activity.base_capacity * 0.6),
                    activity.base_capacity
                )
                
                attending_clients = random.sample(clients, min(num_attendees, len(clients)))
                session.attendees.set(attending_clients)
    
    print(f"  ✓ Creadas sesiones de clases y reservas")


if __name__ == '__main__':
    gym_id = int(sys.argv[1]) if len(sys.argv) > 1 else 1
    create_sample_data(gym_id)
