"""
Script para actualizar los campos de facturación de las membresías existentes
"""
import os
import django
from datetime import timedelta

os.environ.setdefault("DJANGO_SETTINGS_MODULE", "config.settings")
django.setup()

from clients.models import ClientMembership

# Actualizar membresías activas sin fechas de facturación
memberships = ClientMembership.objects.filter(
    status='ACTIVE',
    current_period_start__isnull=True
)

count = 0
for mem in memberships:
    # Establecer periodo actual
    mem.current_period_start = mem.start_date
    
    # Calcular periodo final (30 días para planes mensuales)
    if mem.is_recurring:
        mem.current_period_end = mem.start_date + timedelta(days=30)
        mem.next_billing_date = mem.current_period_end + timedelta(days=1)
    else:
        mem.current_period_end = mem.end_date
        mem.next_billing_date = None
    
    mem.save()
    count += 1
    print(f"✅ Actualizada membresía: {mem.name} - {mem.client.first_name} {mem.client.last_name}")
    print(f"   Periodo: {mem.current_period_start} - {mem.current_period_end}")
    if mem.next_billing_date:
        print(f"   Próximo pago: {mem.next_billing_date}")

print(f"\n✨ Total actualizadas: {count} membresías")
