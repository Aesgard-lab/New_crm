#!/usr/bin/env python
"""
Script para verificar la configuración de Redsys y mostrar datos de prueba
"""
import os
import sys
import django

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'config.settings')
django.setup()

from finance.models import FinanceSettings
from organizations.models import Gym

print("=" * 60)
print("🔍 CONFIGURACIÓN ACTUAL DE REDSYS")
print("=" * 60)

for gym in Gym.objects.all():
    print(f"\n📍 Gimnasio: {gym.name}")
    try:
        fs = gym.finance_settings
        print(f"   Merchant Code (FUC): {fs.redsys_merchant_code or '❌ NO CONFIGURADO'}")
        print(f"   Terminal: {fs.redsys_merchant_terminal or '❌ NO CONFIGURADO'}")
        if fs.redsys_secret_key:
            print(f"   Secret Key: ****{fs.redsys_secret_key[-4:]}")
        else:
            print(f"   Secret Key: ❌ NO CONFIGURADO")
        print(f"   Entorno: {fs.redsys_environment}")
    except FinanceSettings.DoesNotExist:
        print("   ⚠️  SIN CONFIGURACIÓN FINANCIERA")

print("\n")
print("=" * 60)
print("🧪 DATOS DE PRUEBA REDSYS (SANDBOX)")
print("=" * 60)
print("""
📋 CREDENCIALES DE PRUEBA OFICIALES:
   Merchant Code (FUC): 999008881
   Terminal: 1 (o 001)
   Secret Key: sq7HjrUOBfKmC576ILgskD5srU870gJ7
   Entorno: TEST

🌐 URLs SANDBOX:
   API REST: https://sis-t.redsys.es:25443/sis/rest/trataPeticionREST
   TPV Web: https://sis-t.redsys.es:25443/sis/realizarPago

💳 TARJETAS DE PRUEBA:

   ✅ PAGOS APROBADOS:
   ┌─────────────────────────────────────────────────────┐
   │ VISA:       4548 8120 4940 0004                     │
   │ Mastercard: 5576 5700 0000 0004                     │
   │ CVV: 123    Caducidad: 12/30                        │
   └─────────────────────────────────────────────────────┘

   ❌ PAGOS DENEGADOS:
   ┌─────────────────────────────────────────────────────┐
   │ VISA:       4012 0010 3714 1112                     │
   │ CVV: 123    Caducidad: 12/30                        │
   └─────────────────────────────────────────────────────┘

   🔐 3D SECURE:
   ┌─────────────────────────────────────────────────────┐
   │ VISA 3DS:   4918 0190 0000 0008                     │
   │ CVV: 123    Caducidad: 12/30                        │
   │ Código SMS de prueba: 123456                        │
   └─────────────────────────────────────────────────────┘

💡 NOTA: Para usar el entorno de pruebas, asegúrate de que:
   1. El FinanceSettings del gym tenga redsys_environment = 'TEST'
   2. Las credenciales de prueba estén configuradas
""")

# Opción para configurar
print("=" * 60)
print("⚙️  ¿QUIERES CONFIGURAR REDSYS EN SANDBOX PARA UN GYM?")
print("=" * 60)

gyms = list(Gym.objects.all())
if gyms:
    print("\nGimnasios disponibles:")
    for i, gym in enumerate(gyms, 1):
        print(f"  {i}. {gym.name}")
    
    print("\n  0. Salir sin cambios")
    
    try:
        choice = input("\nSelecciona gimnasio (número): ").strip()
        if choice and choice != '0':
            idx = int(choice) - 1
            if 0 <= idx < len(gyms):
                gym = gyms[idx]
                
                fs, created = FinanceSettings.objects.get_or_create(gym=gym)
                
                print(f"\n🔧 Configurando Redsys Sandbox para: {gym.name}")
                
                fs.redsys_merchant_code = '999008881'
                fs.redsys_merchant_terminal = '001'
                fs.redsys_secret_key = 'sq7HjrUOBfKmC576ILgskD5srU870gJ7'
                fs.redsys_environment = 'TEST'
                fs.save()
                
                print("✅ Configuración de Redsys Sandbox guardada!")
                print(f"   Merchant Code: {fs.redsys_merchant_code}")
                print(f"   Terminal: {fs.redsys_merchant_terminal}")
                print(f"   Entorno: {fs.redsys_environment}")
            else:
                print("Número inválido")
    except (ValueError, EOFError):
        print("\nSaliendo...")
else:
    print("\n⚠️  No hay gimnasios en el sistema")
