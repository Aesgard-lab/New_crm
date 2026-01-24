#!/usr/bin/env python
"""
Script para hacer una prueba de pago con Redsys en modo Sandbox
"""
import os
import sys
import django
import json
import requests

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'config.settings')
django.setup()

from organizations.models import Gym
from clients.models import Client, ClientMembership
from finance.models import FinanceSettings
from finance.redsys_utils import get_redsys_client, RedsysClient

print("=" * 60)
print("🧪 PRUEBA DE PAGO REDSYS - SANDBOX")
print("=" * 60)

# 1. Obtener el gimnasio con Redsys configurado
try:
    gym = Gym.objects.get(name='Qombo Arganzuela')
    fs = gym.finance_settings
    print(f"\n✅ Gimnasio: {gym.name}")
    print(f"   Merchant: {fs.redsys_merchant_code}")
    print(f"   Entorno: {fs.redsys_environment}")
except Exception as e:
    print(f"❌ Error: {e}")
    sys.exit(1)

# 2. Buscar un cliente con membresía
print("\n📋 Buscando clientes con membresías...")
clients = Client.objects.filter(gym=gym)[:10]

client_with_membership = None
membership = None

for c in clients:
    memberships = ClientMembership.objects.filter(client=c).first()
    if memberships:
        client_with_membership = c
        membership = memberships
        break

if not client_with_membership:
    print("⚠️  No hay clientes con membresías. Creando datos de prueba...")
    
    # Crear un cliente de prueba
    from memberships.models import MembershipPlan
    from django.contrib.auth.models import User
    from decimal import Decimal
    from django.utils import timezone
    
    # Buscar o crear un plan de membresía
    test_plan, _ = MembershipPlan.objects.get_or_create(
        gym=gym,
        name="Plan Test Redsys",
        defaults={
            'price': Decimal('29.99'),
            'duration_days': 30,
            'is_active': True
        }
    )
    
    # Crear usuario y cliente de prueba
    test_user, _ = User.objects.get_or_create(
        username='test_redsys_user',
        defaults={'email': 'test_redsys@example.com'}
    )
    
    client_with_membership, _ = Client.objects.get_or_create(
        user=test_user,
        gym=gym,
        defaults={
            'first_name': 'Test',
            'last_name': 'Redsys',
            'email': 'test_redsys@example.com',
            'phone': '600000000'
        }
    )
    
    # Crear membresía del cliente
    membership, _ = ClientMembership.objects.get_or_create(
        client=client_with_membership,
        gym=gym,
        name="Plan Test Redsys",
        defaults={
            'plan': test_plan,
            'start_date': timezone.now().date(),
            'end_date': timezone.now().date() + timezone.timedelta(days=30),
            'price': test_plan.price,
            'status': 'PENDING'
        }
    )
    print(f"✅ Cliente de prueba creado: {client_with_membership.first_name} {client_with_membership.last_name}")

print(f"\n👤 Cliente: {client_with_membership.first_name} {client_with_membership.last_name}")
print(f"   Email: {client_with_membership.email}")
print(f"   Membresía: {membership.name}")
print(f"   Precio: {membership.price}€")
print(f"   Estado: {membership.status}")

# 3. Crear el cliente Redsys
print("\n🔧 Inicializando cliente Redsys...")
redsys_client = get_redsys_client(gym)

if not redsys_client:
    print("❌ Error: No se pudo inicializar el cliente Redsys")
    sys.exit(1)

print(f"   URL: {redsys_client.url}")

# 4. Generar orden de pago
import time
order_id = f"{int(time.time())}"[-12:]  # Redsys requiere máximo 12 caracteres

print(f"\n📝 Generando orden de pago...")
print(f"   Order ID: {order_id}")
print(f"   Importe: {membership.price}€")

# URLs de callback (en producción serían URLs reales)
base_url = "http://localhost:8000"
merchant_url = f"{base_url}/finance/redsys/notify/"
url_ok = f"{base_url}/finance/redsys/ok/"
url_ko = f"{base_url}/finance/redsys/ko/"

params = redsys_client.create_request_parameters(
    order_id=order_id,
    amount_eur=float(membership.price),
    transaction_type='0',  # Autorización
    description=f"Membresia: {membership.name}",
    merchant_url=merchant_url,
    url_ok=url_ok,
    url_ko=url_ko
)

print("\n📤 Parámetros generados:")
print(f"   Ds_SignatureVersion: {params['Ds_SignatureVersion']}")
print(f"   Ds_MerchantParameters: {params['Ds_MerchantParameters'][:50]}...")
print(f"   Ds_Signature: {params['Ds_Signature']}")

# 5. Decodificar para mostrar
import base64
decoded_params = json.loads(base64.b64decode(params['Ds_MerchantParameters']))
print("\n📋 Parámetros decodificados:")
for k, v in decoded_params.items():
    print(f"   {k}: {v}")

# 6. Mostrar URL del formulario de pago
print("\n" + "=" * 60)
print("💳 FORMULARIO DE PAGO")
print("=" * 60)

form_url = "https://sis-t.redsys.es:25443/sis/realizarPago"
print(f"""
Para completar el pago, envía un POST a:
{form_url}

Con los siguientes datos:
- Ds_SignatureVersion: {params['Ds_SignatureVersion']}
- Ds_MerchantParameters: {params['Ds_MerchantParameters']}
- Ds_Signature: {params['Ds_Signature']}

💳 USA ESTAS TARJETAS DE PRUEBA:
   VISA OK: 4548 8120 4940 0004
   CVV: 123
   Caducidad: 12/30
""")

# 7. Crear formulario HTML para prueba manual
html_form = f"""<!DOCTYPE html>
<html>
<head>
    <title>Prueba Pago Redsys - Sandbox</title>
    <style>
        body {{ font-family: Arial, sans-serif; max-width: 600px; margin: 50px auto; padding: 20px; }}
        .info {{ background: #e3f2fd; padding: 15px; border-radius: 8px; margin-bottom: 20px; }}
        .card-info {{ background: #e8f5e9; padding: 15px; border-radius: 8px; margin: 20px 0; }}
        button {{ background: #1976d2; color: white; padding: 15px 30px; border: none; border-radius: 8px; cursor: pointer; font-size: 16px; }}
        button:hover {{ background: #1565c0; }}
    </style>
</head>
<body>
    <h1>🧪 Prueba de Pago Redsys</h1>
    
    <div class="info">
        <h3>📋 Datos de la operación:</h3>
        <p><strong>Cliente:</strong> {client_with_membership.first_name} {client_with_membership.last_name}</p>
        <p><strong>Membresía:</strong> {membership.name}</p>
        <p><strong>Importe:</strong> {membership.price}€</p>
        <p><strong>Order ID:</strong> {order_id}</p>
        <p><strong>Entorno:</strong> SANDBOX (Pruebas)</p>
    </div>
    
    <div class="card-info">
        <h3>💳 Datos de tarjeta de prueba:</h3>
        <p><strong>Número:</strong> 4548 8120 4940 0004</p>
        <p><strong>Caducidad:</strong> 12/30</p>
        <p><strong>CVV:</strong> 123</p>
    </div>
    
    <form action="{form_url}" method="POST">
        <input type="hidden" name="Ds_SignatureVersion" value="{params['Ds_SignatureVersion']}">
        <input type="hidden" name="Ds_MerchantParameters" value="{params['Ds_MerchantParameters']}">
        <input type="hidden" name="Ds_Signature" value="{params['Ds_Signature']}">
        
        <button type="submit">💳 Ir al TPV de Redsys (Sandbox)</button>
    </form>
    
    <p style="margin-top: 20px; color: #666;">
        Al hacer clic, serás redirigido al TPV virtual de Redsys en modo pruebas.
    </p>
</body>
</html>
"""

# Guardar el formulario HTML
html_path = os.path.join(os.path.dirname(__file__), 'test_redsys_payment.html')
with open(html_path, 'w', encoding='utf-8') as f:
    f.write(html_form)

print(f"\n✅ Formulario HTML creado: {html_path}")
print("\n🌐 Abre este archivo en tu navegador para probar el pago")
print("   O ejecuta: start test_redsys_payment.html")
