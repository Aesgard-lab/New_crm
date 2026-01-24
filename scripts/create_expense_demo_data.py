"""
Script para crear datos de prueba del módulo de Gastos
"""
import os
import django

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'config.settings')
django.setup()

from finance.models import Supplier, ExpenseCategory, Expense, PaymentMethod
from organizations.models import Gym
from products.models import Product
from django.contrib.auth import get_user_model
from django.utils import timezone
from datetime import timedelta
from decimal import Decimal
from django.db.models import Sum

User = get_user_model()

def create_expense_demo_data():
    """Crear datos de prueba completos para el módulo de gastos"""
    
    # Obtener el gym (asumimos que ya existe)
    gym = Gym.objects.first()
    if not gym:
        print("❌ No hay gimnasios en la base de datos")
        return
    
    print(f"🏢 Usando gym: {gym.name}")
    
    # Obtener usuario admin para created_by
    admin_user = User.objects.filter(is_superuser=True).first()
    if not admin_user:
        admin_user = User.objects.first()
    
    # 1. Crear Proveedores
    print("\n👥 Creando proveedores...")
    suppliers_data = [
        {
            'name': 'Inmobiliaria García SL',
            'tax_id': 'B12345678',
            'email': 'info@inmobiliariagarcia.com',
            'phone': '+34 91 123 45 67',
            'address': 'Calle Mayor, 15, 28001 Madrid',
            'bank_account': 'ES91 2100 0418 4502 0005 1332',
            'contact_person': 'Juan García',
        },
        {
            'name': 'Iberdrola Energía',
            'tax_id': 'A95758389',
            'email': 'empresas@iberdrola.es',
            'phone': '+34 900 100 500',
            'contact_person': 'Atención Empresas',
        },
        {
            'name': 'Vodafone Business',
            'tax_id': 'A80907397',
            'email': 'business@vodafone.es',
            'phone': '+34 123 456 789',
            'contact_person': 'Gestor de Cuenta',
        },
        {
            'name': 'Fitness Equipment Pro',
            'tax_id': 'B87654321',
            'email': 'ventas@fitnesspro.com',
            'phone': '+34 654 321 987',
            'address': 'Polígono Industrial Norte, Nave 12, 28850 Madrid',
            'bank_account': 'ES12 0182 1234 5678 9012 3456',
            'contact_person': 'Carlos Martínez',
        },
        {
            'name': 'CleanPro Servicios',
            'tax_id': 'B11223344',
            'email': 'info@cleanpro.es',
            'phone': '+34 666 777 888',
            'contact_person': 'María López',
        },
    ]
    
    suppliers = []
    for data in suppliers_data:
        supplier, created = Supplier.objects.get_or_create(
            gym=gym,
            name=data['name'],
            defaults={**data}
        )
        suppliers.append(supplier)
        status = "✅ Creado" if created else "⏩ Ya existe"
        print(f"  {status}: {supplier.name}")
    
    # 2. Crear Categorías
    print("\n🏷️ Creando categorías de gastos...")
    categories_data = [
        {'name': 'Alquiler', 'color': '#ef4444', 'icon': '🏠', 'description': 'Alquiler de local'},
        {'name': 'Suministros', 'color': '#f59e0b', 'icon': '💡', 'description': 'Luz, agua, gas'},
        {'name': 'Telecomunicaciones', 'color': '#3b82f6', 'icon': '📡', 'description': 'Internet, teléfono, TV'},
        {'name': 'Equipamiento', 'color': '#8b5cf6', 'icon': '🏋️', 'description': 'Máquinas, pesas, equipamiento'},
        {'name': 'Limpieza', 'color': '#10b981', 'icon': '🧹', 'description': 'Servicios de limpieza'},
        {'name': 'Marketing', 'color': '#ec4899', 'icon': '📱', 'description': 'Publicidad y promoción'},
        {'name': 'Software', 'color': '#06b6d4', 'icon': '💻', 'description': 'Licencias y herramientas'},
        {'name': 'Mantenimiento', 'color': '#f97316', 'icon': '🔧', 'description': 'Reparaciones y mantenimiento'},
    ]
    
    categories = []
    for data in categories_data:
        category, created = ExpenseCategory.objects.get_or_create(
            gym=gym,
            name=data['name'],
            defaults={**data}
        )
        categories.append(category)
        status = "✅ Creado" if created else "⏩ Ya existe"
        print(f"  {status}: {data['icon']} {category.name}")
    
    # 3. Obtener método de pago (o crear uno por defecto)
    payment_method = PaymentMethod.objects.filter(gym=gym).first()
    if not payment_method:
        payment_method = PaymentMethod.objects.create(
            gym=gym,
            name='Transferencia Bancaria',
            is_active=True
        )
        print(f"\n💳 Método de pago creado: {payment_method.name}")
    
    # 4. Crear Gastos de Ejemplo
    print("\n💸 Creando gastos de ejemplo...")
    
    today = timezone.now().date()
    
    expenses_data = [
        # GASTO RECURRENTE: Alquiler
        {
            'supplier': suppliers[0],  # Inmobiliaria
            'category': categories[0],  # Alquiler
            'concept': 'Alquiler Local Comercial - Enero 2025',
            'reference_number': 'ALQ-2025-01',
            'description': 'Alquiler mensual del local de 300m²',
            'base_amount': Decimal('3000.00'),
            'tax_rate': Decimal('21.00'),
            'issue_date': today - timedelta(days=25),
            'due_date': today - timedelta(days=20),
            'payment_date': today - timedelta(days=18),
            'status': 'PAID',
            'payment_method': payment_method,
            'is_recurring': True,
            'recurrence_frequency': 'MONTHLY',
            'recurrence_day': 1,
            'is_active_recurrence': True,
        },
        # GASTO RECURRENTE: Electricidad
        {
            'supplier': suppliers[1],  # Iberdrola
            'category': categories[1],  # Suministros
            'concept': 'Factura Electricidad Diciembre 2024',
            'reference_number': 'ELEC-2024-12',
            'description': 'Consumo eléctrico del gimnasio',
            'base_amount': Decimal('850.50'),
            'tax_rate': Decimal('21.00'),
            'issue_date': today - timedelta(days=15),
            'due_date': today + timedelta(days=5),
            'status': 'PENDING',
            'is_recurring': True,
            'recurrence_frequency': 'MONTHLY',
            'recurrence_day': 15,
            'is_active_recurrence': True,
        },
        # GASTO VENCIDO: Internet
        {
            'supplier': suppliers[2],  # Vodafone
            'category': categories[2],  # Telecomunicaciones
            'concept': 'Fibra 1GB + Líneas Móviles',
            'reference_number': 'VOD-2024-11',
            'base_amount': Decimal('120.00'),
            'tax_rate': Decimal('21.00'),
            'issue_date': today - timedelta(days=40),
            'due_date': today - timedelta(days=10),
            'status': 'OVERDUE',
            'is_recurring': True,
            'recurrence_frequency': 'MONTHLY',
            'recurrence_day': 1,
            'is_active_recurrence': True,
        },
        # GASTO PUNTUAL: Equipamiento
        {
            'supplier': suppliers[3],  # Fitness Equipment
            'category': categories[3],  # Equipamiento
            'concept': 'Compra Cinta de Correr Pro X5',
            'reference_number': 'FEP-2025-001',
            'description': 'Cinta de correr profesional con pantalla táctil',
            'base_amount': Decimal('4500.00'),
            'tax_rate': Decimal('21.00'),
            'issue_date': today - timedelta(days=10),
            'due_date': today + timedelta(days=20),
            'status': 'PENDING',
            'is_recurring': False,
        },
        # GASTO PARCIALMENTE PAGADO: Limpieza
        {
            'supplier': suppliers[4],  # CleanPro
            'category': categories[4],  # Limpieza
            'concept': 'Servicios de Limpieza Q4 2024',
            'reference_number': 'CLN-2024-Q4',
            'description': 'Limpieza profesional 3 veces por semana',
            'base_amount': Decimal('1200.00'),
            'tax_rate': Decimal('21.00'),
            'issue_date': today - timedelta(days=5),
            'due_date': today + timedelta(days=15),
            'status': 'PARTIAL',
            'paid_amount': Decimal('726.00'),  # 50% pagado
            'is_recurring': True,
            'recurrence_frequency': 'QUARTERLY',
            'recurrence_day': 1,
            'is_active_recurrence': True,
        },
    ]
    
    for data in expenses_data:
        expense, created = Expense.objects.get_or_create(
            gym=gym,
            concept=data['concept'],
            defaults={
                **data,
                'created_by': admin_user
            }
        )
        status = "✅ Creado" if created else "⏩ Ya existe"
        recurring_badge = "🔄" if expense.is_recurring else "📄"
        status_emoji = {
            'PAID': '✅',
            'PENDING': '⏳',
            'OVERDUE': '🚨',
            'PARTIAL': '⚠️'
        }.get(expense.status, '❓')
        
        print(f"  {status}: {recurring_badge} {status_emoji} {expense.concept} - {expense.total_amount}€")
    
    # 5. Enlazar productos con gastos (si existen productos)
    products = Product.objects.filter(gym=gym)[:3]
    if products.exists():
        print(f"\n🛒 Enlazando {products.count()} productos con gastos...")
        equipment_expense = Expense.objects.filter(
            gym=gym,
            category=categories[3]
        ).first()
        
        if equipment_expense:
            equipment_expense.related_products.set(products)
            print(f"  ✅ Productos enlazados con: {equipment_expense.concept}")
    
    print("\n" + "="*70)
    print("✅ DATOS DE PRUEBA CREADOS CORRECTAMENTE")
    print("="*70)
    
    # Resumen
    print(f"\n📊 RESUMEN:")
    print(f"  👥 Proveedores: {Supplier.objects.filter(gym=gym).count()}")
    print(f"  🏷️ Categorías: {ExpenseCategory.objects.filter(gym=gym).count()}")
    print(f"  💸 Gastos: {Expense.objects.filter(gym=gym).count()}")
    print(f"    🔄 Recurrentes: {Expense.objects.filter(gym=gym, is_recurring=True).count()}")
    print(f"    ✅ Pagados: {Expense.objects.filter(gym=gym, status='PAID').count()}")
    print(f"    ⏳ Pendientes: {Expense.objects.filter(gym=gym, status='PENDING').count()}")
    print(f"    🚨 Vencidos: {Expense.objects.filter(gym=gym, status='OVERDUE').count()}")
    
    total_expenses = Expense.objects.filter(gym=gym).aggregate(
        total=Sum('total_amount')
    )['total'] or Decimal('0')
    
    print(f"\n💰 Total en Gastos: {total_expenses}€")
    print(f"\n🌐 Accede al módulo en: /finance/expenses/")
    print("="*70)

if __name__ == '__main__':
    create_expense_demo_data()
