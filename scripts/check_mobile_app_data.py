"""
Script para verificar datos de prueba en el backend para la app móvil.
"""
import os
import django

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'config.settings')
django.setup()

from clients.models import Client, ClientMembership, DocumentTemplate
from activities.models import Activity, ActivitySession
from routines.models import WorkoutRoutine
from products.models import Product
from django.utils import timezone
from datetime import timedelta

def check_mobile_app_data():
    print("=" * 60)
    print("VERIFICACIÓN DE DATOS PARA APP MÓVIL")
    print("=" * 60)
    
    # 1. Clientes con usuario
    clients_with_user = Client.objects.filter(user__isnull=False)
    print(f"\n✓ Clientes con usuario: {clients_with_user.count()}")
    if clients_with_user.exists():
        for client in clients_with_user[:5]:
            print(f"  - {client.first_name} {client.last_name} ({client.email})")
            print(f"    Access Code: {client.access_code}")
    
    # 2. Membresías activas
    active_memberships = ClientMembership.objects.filter(status='ACTIVE').select_related('client', 'plan')
    print(f"\n✓ Membresías activas: {active_memberships.count()}")
    if active_memberships.exists():
        for membership in active_memberships[:5]:
            plan_name = membership.plan.name if membership.plan else 'Sin plan'
            print(f"  - {membership.client.first_name} {membership.client.last_name}: {plan_name}")
            print(f"    Hasta: {membership.end_date}")
    
    # 3. Actividades
    activities = Activity.objects.all()
    print(f"\n✓ Actividades: {activities.count()}")
    if activities.exists():
        for activity in activities[:5]:
            print(f"  - {activity.name}")
    
    # 4. Sesiones
    sessions = ActivitySession.objects.all().select_related('activity')[:10]
    print(f"\n✓ Sesiones totales: {ActivitySession.objects.count()}")
    if sessions.exists():
        for session in sessions[:5]:
            print(f"  - {session.activity.name}: {session.start_datetime}")
            print(f"    Capacidad: {session.max_capacity}")
    
    # 5. Rutinas
    routines = WorkoutRoutine.objects.filter(is_template=True)
    print(f"\n✓ Rutinas activas: {routines.count()}")
    if routines.exists():
        for routine in routines[:5]:
            print(f"  - {routine.name} ({routine.goal})")
    
    # 6. Productos
    products = Product.objects.filter(is_active=True)
    print(f"\n✓ Productos en tienda: {products.count()}")
    if products.exists():
        for product in products[:5]:
            print(f"  - {product.name}: ${product.base_price}")
    
    # 7. Documentos
    documents = DocumentTemplate.objects.all()
    print(f"\n✓ Plantillas de documentos: {documents.count()}")
    if documents.exists():
        for doc in documents[:5]:
            print(f"  - {doc.title}")
    
    print("\n" + "=" * 60)
    print("RECOMENDACIONES")
    print("=" * 60)
    
    warnings = []
    
    if clients_with_user.count() == 0:
        warnings.append("⚠️  NO HAY CLIENTES CON USUARIO - La app no podrá hacer login")
        print("\nPara crear un cliente de prueba:")
        print("  1. Ir a /admin/clients/client/")
        print("  2. Crear cliente con email")
        print("  3. Marcar 'Has user account'")
        print("  4. El sistema creará automáticamente el usuario")
    
    if active_memberships.count() == 0:
        warnings.append("⚠️  NO HAY MEMBRESÍAS ACTIVAS")
    
    if sessions.count() == 0:
        warnings.append("⚠️  NO HAY SESIONES - El calendario estará vacío")
        print("\nPara crear sesiones:")
        print("  python create_sample_data.py")
    
    if routines.count() == 0:
        warnings.append("⚠️  NO HAY RUTINAS - La sección de rutinas estará vacía")
    
    if not warnings:
        print("\n✅ TODOS LOS DATOS NECESARIOS ESTÁN PRESENTES")
        print("\nPara probar la app:")
        print("  1. cd mobile_app")
        print("  2. flutter pub get")
        print("  3. flutter run")
        print("\nCredenciales de prueba:")
        if clients_with_user.exists():
            client = clients_with_user.first()
            print(f"  Email: {client.email}")
            print(f"  Password: (la que hayas configurado)")
    else:
        print("\n❌ PROBLEMAS DETECTADOS:")
        for warning in warnings:
            print(f"  {warning}")

if __name__ == '__main__':
    check_mobile_app_data()
