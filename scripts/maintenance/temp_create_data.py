"""
Script temporal para crear datos de prueba completos
"""
import os
import sys
import django
import random
from datetime import timedelta, datetime
from decimal import Decimal

# Setup Django
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'config.settings.local')
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
django.setup()

from django.utils import timezone
from django.contrib.auth import get_user_model
from organizations.models import Franchise, Gym
from clients.models import Client, ClientMembership
from activities.models import Activity, ActivitySession, ActivitySessionBooking
from memberships.models import MembershipPlan
from products.models import Product, ProductCategory
from services.models import Service, ServiceCategory
from finance.models import PaymentMethod, TaxRate
from sales.models import Order, OrderItem
from staff.models import StaffProfile
from accounts.models_memberships import GymMembership, FranchiseMembership

User = get_user_model()

def create_all_data():
    print("\n" + "="*60)
    print("🚀 CREANDO DATOS DE PRUEBA COMPLETOS")
    print("="*60)
    
    # ===================================================================
    # 1. CREAR FRANQUICIA QOMBO
    # ===================================================================
    print("\n📌 PASO 1: Franquicia Qombo")
    
    owner_email = 'owner@qombo.com'
    owner, created = User.objects.get_or_create(email=owner_email)
    if created:
        owner.set_password('qombo123')
        owner.first_name = 'Sr. Qombo'
        owner.is_staff = True
        owner.save()
        print(f'  ✅ Usuario Owner creado: {owner_email} / qombo123')
    else:
        print(f'  ℹ️  Usuario Owner ya existe: {owner_email}')
    
    franchise, created = Franchise.objects.get_or_create(name='Qombo')
    franchise.owners.add(owner)
    print(f'  ✅ Franquicia: {franchise.name}')
    
    # ===================================================================
    # 2. CREAR GIMNASIOS
    # ===================================================================
    print("\n📌 PASO 2: Gimnasios")
    
    gyms_data = [
        {'name': 'Qombo Madrid Central', 'city': 'Madrid'},
        {'name': 'Qombo Barcelona Beach', 'city': 'Barcelona'},
        {'name': 'Qombo Valencia City', 'city': 'Valencia'},
        {'name': 'Qombo Sevilla Sur', 'city': 'Sevilla'},
    ]
    
    gyms = []
    for g_data in gyms_data:
        gym, created = Gym.objects.get_or_create(
            franchise=franchise,
            name=g_data['name'],
            defaults={
                'commercial_name': g_data['name'],
                'city': g_data['city'],
                'country': 'España',
                'email': f"info@{g_data['city'].lower()}.qombo.com",
                'phone': '+34 900 123 456'
            }
        )
        gyms.append(gym)
        status = "Creado" if created else "Ya existe"
        print(f'  ✅ {gym.name} ({status})')
    
    # ===================================================================
    # 2.5 CREAR STAFF Y OWNERS PARA CADA GIMNASIO
    # ===================================================================
    print("\n📌 PASO 2.5: Staff y Owners")
    
    staff_data = [
        {'first': 'Carlos', 'last': 'Gerente', 'role': 'MANAGER', 'color': '#ef4444'},
        {'first': 'Laura', 'last': 'Trainer', 'role': 'TRAINER', 'color': '#22c55e'},
        {'first': 'Miguel', 'last': 'Trainer', 'role': 'TRAINER', 'color': '#3b82f6'},
        {'first': 'Ana', 'last': 'Recepcion', 'role': 'RECEPTIONIST', 'color': '#f97316'},
        {'first': 'Pedro', 'last': 'Trainer', 'role': 'TRAINER', 'color': '#a855f7'},
    ]
    
    staff_created = 0
    owners_created = 0
    
    for gym in gyms:
        city_code = gym.city[:3].lower() if gym.city else 'gym'
        
        # Crear Owner/Admin del gimnasio
        admin_email = f'admin.{city_code}@qombo.com'
        admin_user, created = User.objects.get_or_create(
            email=admin_email,
            defaults={
                'first_name': f'Admin',
                'last_name': gym.city or 'Gym',
                'is_staff': True,
                'is_active': True
            }
        )
        if created:
            admin_user.set_password('admin123')
            admin_user.save()
            owners_created += 1
        
        # Asignar como ADMIN del gimnasio
        GymMembership.objects.get_or_create(
            user=admin_user,
            gym=gym,
            defaults={'role': 'ADMIN', 'is_active': True}
        )
        
        # Crear Staff profiles
        for idx, s_data in enumerate(staff_data):
            staff_email = f"{s_data['first'].lower()}.{s_data['last'].lower()}.{city_code}{idx}@qombo.com"
            
            staff_user, created = User.objects.get_or_create(
                email=staff_email,
                defaults={
                    'first_name': s_data['first'],
                    'last_name': s_data['last'],
                    'is_active': True
                }
            )
            if created:
                staff_user.set_password('staff123')
                staff_user.save()
            
            # Crear GymMembership como STAFF
            GymMembership.objects.get_or_create(
                user=staff_user,
                gym=gym,
                defaults={'role': 'STAFF', 'is_active': True}
            )
            
            # Crear StaffProfile
            profile, created = StaffProfile.objects.get_or_create(
                user=staff_user,
                gym=gym,
                defaults={
                    'role': s_data['role'],
                    'color': s_data['color'],
                    'bio': f"Profesional de {s_data['role'].lower()} en {gym.name}",
                    'pin_code': f'{1000 + idx + gym.id}',
                    'is_active': True
                }
            )
            if created:
                staff_created += 1
    
    print(f'  ✅ {owners_created} owners/admins creados')
    print(f'  ✅ {staff_created} staff profiles creados')
    print(f'  📊 Total usuarios staff: {User.objects.filter(is_staff=True).count()}')
    
    # ===================================================================
    # 3. CREAR CLIENTES
    # ===================================================================
    print("\n📌 PASO 3: Clientes")
    
    nombres = ['Juan', 'Maria', 'Pedro', 'Ana', 'Carlos', 'Laura', 'Miguel', 'Sofia', 
               'Diego', 'Elena', 'Pablo', 'Carmen', 'Javier', 'Isabel', 'Fernando', 
               'Lucia', 'Rafael', 'Marta', 'Antonio', 'Patricia', 'Jose', 'Cristina', 
               'Manuel', 'Paula', 'David', 'Raquel', 'Luis', 'Beatriz', 'Alberto', 'Gloria']
    apellidos = ['Garcia', 'Martinez', 'Lopez', 'Sanchez', 'Gonzalez', 'Rodriguez', 
                 'Fernandez', 'Perez', 'Ruiz', 'Diaz', 'Hernandez', 'Moreno', 
                 'Alvarez', 'Jimenez', 'Torres', 'Romero']
    
    for gym in gyms:
        existing = Client.objects.filter(gym=gym).count()
        if existing < 25:
            num_to_create = 25 - existing
            for i in range(num_to_create):
                nombre = random.choice(nombres)
                apellido = random.choice(apellidos)
                Client.objects.create(
                    gym=gym,
                    first_name=nombre,
                    last_name=apellido,
                    email=f'{nombre.lower()}.{apellido.lower()}{i}@test{gym.id}.com',
                    phone_number=f'+34 6{random.randint(10,99)} {random.randint(100,999)} {random.randint(100,999)}',
                    status=random.choice(['ACTIVE', 'ACTIVE', 'ACTIVE', 'INACTIVE', 'PROSPECT'])
                )
            print(f'  ✅ {gym.name}: {num_to_create} clientes creados')
        else:
            print(f'  ℹ️  {gym.name}: {existing} clientes ya existen')
    
    print(f'  📊 Total clientes: {Client.objects.count()}')
    
    # ===================================================================
    # 4. CREAR ACTIVIDADES
    # ===================================================================
    print("\n📌 PASO 4: Actividades")
    
    actividades_data = [
        {'name': 'Spinning', 'duration': 45, 'capacity': 20, 'color': '#ef4444'},
        {'name': 'Yoga', 'duration': 60, 'capacity': 15, 'color': '#22c55e'},
        {'name': 'CrossFit', 'duration': 50, 'capacity': 12, 'color': '#3b82f6'},
        {'name': 'Pilates', 'duration': 55, 'capacity': 10, 'color': '#a855f7'},
        {'name': 'Boxeo', 'duration': 45, 'capacity': 16, 'color': '#f97316'},
        {'name': 'Zumba', 'duration': 50, 'capacity': 25, 'color': '#ec4899'},
        {'name': 'BodyPump', 'duration': 55, 'capacity': 20, 'color': '#14b8a6'},
    ]
    
    for gym in gyms:
        created_count = 0
        for act_data in actividades_data:
            activity, created = Activity.objects.get_or_create(
                gym=gym,
                name=act_data['name'],
                defaults={
                    'description': f"Clase de {act_data['name']}",
                    'duration': act_data['duration'],
                    'base_capacity': act_data['capacity'],
                    'color': act_data['color'],
                    'is_visible_online': True
                }
            )
            if created:
                created_count += 1
        print(f'  ✅ {gym.name}: {created_count} actividades creadas')
    
    # ===================================================================
    # 5. CREAR SESIONES DE ACTIVIDADES
    # ===================================================================
    print("\n📌 PASO 5: Sesiones de Actividades")
    
    now = timezone.now()
    sessions_created = 0
    
    for gym in gyms:
        activities = Activity.objects.filter(gym=gym)
        for activity in activities:
            for day_offset in range(7):
                session_date = now.date() + timedelta(days=day_offset)
                hours = [9, 11, 17, 19]
                for hour in hours:
                    session_datetime = timezone.make_aware(
                        datetime.combine(session_date, datetime.min.time().replace(hour=hour, minute=0))
                    )
                    session, created = ActivitySession.objects.get_or_create(
                        gym=gym,
                        activity=activity,
                        start_datetime=session_datetime,
                        defaults={
                            'end_datetime': session_datetime + timedelta(minutes=activity.duration),
                            'max_capacity': activity.base_capacity,
                            'status': 'SCHEDULED'
                        }
                    )
                    if created:
                        sessions_created += 1
    
    print(f'  ✅ {sessions_created} sesiones creadas')
    
    # ===================================================================
    # 6. CREAR RESERVAS
    # ===================================================================
    print("\n📌 PASO 6: Reservas")
    
    bookings_created = 0
    for gym in gyms:
        clients = list(Client.objects.filter(gym=gym, status='ACTIVE')[:15])
        sessions = list(ActivitySession.objects.filter(
            gym=gym, 
            start_datetime__gte=now,
            start_datetime__lte=now + timedelta(days=5)
        )[:30])
        
        for session in sessions:
            num_bookings = random.randint(2, min(6, session.max_capacity))
            for client in random.sample(clients, min(num_bookings, len(clients))):
                booking, created = ActivitySessionBooking.objects.get_or_create(
                    client=client,
                    session=session,
                    defaults={
                        'status': 'CONFIRMED',
                        'attendance_status': 'PENDING'
                    }
                )
                if created:
                    bookings_created += 1
    
    print(f'  ✅ {bookings_created} reservas creadas')
    
    # ===================================================================
    # 7. CREAR PLANES DE MEMBRESÍA
    # ===================================================================
    print("\n📌 PASO 7: Planes de Membresía")
    
    planes_data = [
        {'name': 'Plan Básico', 'price': Decimal('29.99'), 'freq': 1, 'unit': 'MONTH'},
        {'name': 'Plan Premium', 'price': Decimal('49.99'), 'freq': 1, 'unit': 'MONTH'},
        {'name': 'Plan Anual', 'price': Decimal('399.99'), 'freq': 1, 'unit': 'YEAR'},
        {'name': 'Bono 10 Clases', 'price': Decimal('89.99'), 'freq': 0, 'unit': 'MONTH'},
    ]
    
    for gym in gyms:
        for plan_data in planes_data:
            plan, created = MembershipPlan.objects.get_or_create(
                gym=gym,
                name=plan_data['name'],
                defaults={
                    'description': f"Plan de membresía {plan_data['name']}",
                    'base_price': plan_data['price'],
                    'frequency_amount': plan_data['freq'],
                    'frequency_unit': plan_data['unit'],
                    'is_recurring': plan_data['freq'] > 0,
                    'is_active': True,
                    'is_membership': True
                }
            )
            if created:
                print(f'  ✅ {gym.name}: {plan.name}')
    
    # ===================================================================
    # 8. ASIGNAR MEMBRESÍAS A CLIENTES
    # ===================================================================
    print("\n📌 PASO 8: Membresías de Clientes")
    
    memberships_created = 0
    for gym in gyms:
        clients = Client.objects.filter(gym=gym, status='ACTIVE')
        plans = list(MembershipPlan.objects.filter(gym=gym, is_active=True))
        
        for client in clients:
            if not ClientMembership.objects.filter(client=client).exists() and plans:
                plan = random.choice(plans)
                ClientMembership.objects.create(
                    client=client,
                    gym=gym,
                    plan=plan,
                    name=plan.name,
                    start_date=now.date() - timedelta(days=random.randint(1, 30)),
                    end_date=now.date() + timedelta(days=random.randint(15, 60)),
                    price=plan.base_price,
                    status='ACTIVE',
                    is_recurring=plan.is_recurring
                )
                memberships_created += 1
    
    print(f'  ✅ {memberships_created} membresías asignadas')
    
    # ===================================================================
    # 9. CREAR PRODUCTOS Y SERVICIOS
    # ===================================================================
    print("\n📌 PASO 9: Productos y Servicios")
    
    for gym in gyms:
        # Categorías
        p_cat, _ = ProductCategory.objects.get_or_create(gym=gym, name="Nutrición")
        s_cat, _ = ServiceCategory.objects.get_or_create(gym=gym, name="Entrenamientos")
        
        # Tax
        tax, _ = TaxRate.objects.get_or_create(gym=gym, name="IVA 21%", defaults={'rate_percent': Decimal('21.00')})
        
        # Productos
        productos_data = [
            {'name': 'Proteína Whey 1kg', 'price': Decimal('45.00')},
            {'name': 'Barrita Energética', 'price': Decimal('2.50')},
            {'name': 'Bebida Isotónica', 'price': Decimal('3.00')},
            {'name': 'Toalla Gym', 'price': Decimal('15.00')},
        ]
        
        for p_data in productos_data:
            Product.objects.get_or_create(
                gym=gym, 
                name=p_data['name'],
                defaults={
                    'base_price': p_data['price'],
                    'tax_rate': tax,
                    'category': p_cat,
                    'is_active': True
                }
            )
        
        # Servicios
        servicios_data = [
            {'name': 'Pase Diario', 'price': Decimal('10.00')},
            {'name': 'Clase Suelta', 'price': Decimal('15.00')},
            {'name': 'Entrenamiento Personal', 'price': Decimal('35.00')},
            {'name': 'Plan Nutrición', 'price': Decimal('50.00')},
        ]
        
        for s_data in servicios_data:
            Service.objects.get_or_create(
                gym=gym,
                name=s_data['name'],
                defaults={
                    'base_price': s_data['price'],
                    'tax_rate': tax,
                    'category': s_cat,
                    'is_active': True
                }
            )
        
        # Métodos de pago
        PaymentMethod.objects.get_or_create(gym=gym, name="Efectivo", defaults={'is_cash': True, 'is_active': True})
        PaymentMethod.objects.get_or_create(gym=gym, name="Tarjeta", defaults={'is_cash': False, 'is_active': True})
    
    print(f'  ✅ Productos: {Product.objects.count()}')
    print(f'  ✅ Servicios: {Service.objects.count()}')
    
    # ===================================================================
    # 10. CREAR VENTAS/COMPRAS (sin signals para evitar error de Celery)
    # ===================================================================
    print("\n📌 PASO 10: Ventas")
    
    # Usar bulk_create con update_or_create para evitar signals
    from django.db import connection
    
    orders_created = 0
    for gym in gyms:
        clients = list(Client.objects.filter(gym=gym)[:10])
        staff = User.objects.filter(is_staff=True).first()
        
        for i in range(15):
            if clients:
                client = random.choice(clients)
                total = Decimal(random.choice([29.99, 49.99, 89.99, 45.00, 15.00]))
                
                # Inserción directa en SQL para evitar signals
                with connection.cursor() as cursor:
                    cursor.execute("""
                        INSERT INTO sales_order (gym_id, client_id, created_by_id, status, 
                                                total_base, total_tax, total_discount, total_amount, 
                                                total_refunded, auto_charge, internal_notes, 
                                                deferred_notes, created_at, updated_at)
                        VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, datetime('now'), datetime('now'))
                    """, [gym.id, client.id, staff.id if staff else None, 'PAID', 
                          float(total), 0.0, 0.0, float(total), 0.0, False, '', ''])
                orders_created += 1
    
    print(f'  ✅ {orders_created} ventas creadas')
    
    # ===================================================================
    # RESUMEN FINAL
    # ===================================================================
    print("\n" + "="*60)
    print("🎉 DATOS DE PRUEBA CREADOS EXITOSAMENTE")
    print("="*60)
    print(f"""
📊 RESUMEN:
   • Franquicia: {Franchise.objects.count()}
   • Gimnasios: {Gym.objects.count()}
   • Staff Profiles: {StaffProfile.objects.count()}
   • GymMemberships (admins/staff): {GymMembership.objects.count()}
   • Clientes: {Client.objects.count()}
   • Actividades: {Activity.objects.count()}
   • Sesiones: {ActivitySession.objects.count()}
   • Reservas: {ActivitySessionBooking.objects.count()}
   • Planes: {MembershipPlan.objects.count()}
   • Membresías: {ClientMembership.objects.count()}
   • Productos: {Product.objects.count()}
   • Servicios: {Service.objects.count()}
   • Ventas: {Order.objects.count()}

🔑 CREDENCIALES:
   • Superadmin: santiagoexplo@hotmail.com / 123
   • Owner Franquicia: owner@qombo.com / qombo123
   • Admin por Gym: admin.<ciudad>@qombo.com / admin123
     (ej: admin.mad@qombo.com, admin.bar@qombo.com)
   • Staff: <nombre>.<rol>.<ciudad>@qombo.com / staff123
     (ej: carlos.gerente.mad0@qombo.com)
   
🌐 URLs:
   • Admin: http://127.0.0.1:8000/superadmin/
   • Backoffice: http://127.0.0.1:8000/backoffice/
    """)

if __name__ == "__main__":
    create_all_data()
