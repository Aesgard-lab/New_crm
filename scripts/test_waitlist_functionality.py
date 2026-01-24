"""
Script para probar funcionalidad de lista de espera
- Llena una clase hasta el máximo de aforo
- Añade clientes a la lista de espera
- Verifica que cuando se elimina un asistente, el primero de la lista se promueve
"""
import os
import django

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'config.settings')
django.setup()

from clients.models import Client
from activities.models import ActivitySession, WaitlistEntry
from django.utils import timezone
from datetime import timedelta

def run_test():
    print("🧪 Iniciando test de funcionalidad de lista de espera")
    print("="*60)
    
    # Buscar una sesión con capacidad limitada
    session = ActivitySession.objects.filter(
        status='SCHEDULED',
        start_datetime__gte=timezone.now(),
        max_capacity__lte=15  # Buscamos una clase pequeña para llenar fácil
    ).first()
    
    if not session:
        print("❌ No se encontró ninguna sesión programada")
        return
    
    print(f"\n📅 Sesión seleccionada: {session.activity.name}")
    print(f"   Fecha: {session.start_datetime.strftime('%d/%m/%Y %H:%M')}")
    print(f"   Capacidad máxima: {session.max_capacity}")
    print(f"   Asistentes actuales: {session.attendees.count()}")
    print(f"   En lista de espera: {session.waitlist_entries.filter(status='WAITING').count()}")
    
    # Limpiar la sesión primero
    print("\n🧹 Limpiando sesión...")
    session.attendees.clear()
    session.waitlist_entries.all().delete()
    
    # Obtener clientes activos
    clients = list(Client.objects.filter(
        gym=session.gym,
        status='ACTIVE'
    )[:session.max_capacity + 5])  # Traemos más de los que caben
    
    if len(clients) < session.max_capacity + 3:
        print(f"❌ No hay suficientes clientes activos. Se necesitan al menos {session.max_capacity + 3}")
        return
    
    # Llenar la clase hasta el máximo
    print(f"\n📝 Llenando clase hasta capacidad máxima ({session.max_capacity} clientes)...")
    for i in range(session.max_capacity):
        client = clients[i]
        session.attendees.add(client)
        print(f"   ✓ Añadido: {client.first_name} {client.last_name}")
    
    print(f"\n✅ Clase llena: {session.attendees.count()}/{session.max_capacity}")
    
    # Añadir clientes a lista de espera
    waitlist_clients = clients[session.max_capacity:session.max_capacity + 3]
    print(f"\n⏳ Añadiendo {len(waitlist_clients)} clientes a lista de espera...")
    for i, client in enumerate(waitlist_clients, 1):
        entry = WaitlistEntry.objects.create(
            session=session,
            client=client,
            gym=session.gym,
            status='WAITING',
            joined_at=timezone.now() + timedelta(seconds=i)  # Orden de llegada
        )
        print(f"   #{i} {client.first_name} {client.last_name}")
    
    # Verificar estado
    print("\n" + "="*60)
    print("📊 ESTADO ACTUAL DE LA CLASE:")
    print("="*60)
    print(f"Asistentes confirmados: {session.attendees.count()}/{session.max_capacity}")
    print(f"En lista de espera: {session.waitlist_entries.filter(status='WAITING').count()}")
    
    # Mostrar lista de espera
    print("\n📋 Lista de espera (en orden):")
    for entry in session.waitlist_entries.filter(status='WAITING').order_by('joined_at'):
        print(f"   • {entry.client.first_name} {entry.client.last_name} - {entry.joined_at.strftime('%H:%M:%S')}")
    
    print("\n" + "="*60)
    print("✅ Test completado")
    print("="*60)
    print("\n📝 Instrucciones para continuar el test:")
    print(f"1. Abre el calendario en: http://127.0.0.1:8000/activities/calendar/")
    print(f"2. Busca la clase: {session.activity.name} - {session.start_datetime.strftime('%d/%m/%Y %H:%M')}")
    print(f"3. Verifica que aparezcan {session.max_capacity} asistentes")
    print(f"4. Verifica que aparezca la lista de espera con {len(waitlist_clients)} personas")
    print(f"5. Elimina un asistente de la clase")
    print(f"6. Verifica que automáticamente se añada el primero de la lista de espera")
    print("\n💡 IMPORTANTE: Asegúrate de que la actividad '{session.activity.name}'")
    print("   tenga activada la opción 'Permitir lista de espera'")

if __name__ == '__main__':
    run_test()
