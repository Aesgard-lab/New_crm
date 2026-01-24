"""
Script de migración: Crear bookings para asistentes existentes
Ejecutar una sola vez para backfill de datos históricos.

Uso:
    python create_bookings_backfill.py
"""
import os
import django

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'config.settings')
django.setup()

from activities.models import ActivitySession, ActivitySessionBooking
from django.db import transaction


def backfill_bookings():
    """Crea registros de booking para todos los asistentes existentes."""
    
    print("🔄 Iniciando backfill de bookings...")
    
    sessions = ActivitySession.objects.filter(
        status__in=['SCHEDULED', 'COMPLETED']
    ).prefetch_related('attendees')
    
    total_sessions = sessions.count()
    created_bookings = 0
    existing_bookings = 0
    
    print(f"📊 Procesando {total_sessions} sesiones...")
    
    with transaction.atomic():
        for i, session in enumerate(sessions, 1):
            if i % 100 == 0:
                print(f"  Progreso: {i}/{total_sessions} sesiones ({(i/total_sessions)*100:.1f}%)")
            
            for client in session.attendees.all():
                booking, created = ActivitySessionBooking.objects.get_or_create(
                    session=session,
                    client=client,
                    defaults={
                        'status': 'CONFIRMED',
                        'attendance_status': 'PENDING'
                    }
                )
                
                if created:
                    created_bookings += 1
                else:
                    existing_bookings += 1
    
    print("\n✅ Backfill completado!")
    print(f"   📝 Bookings creados: {created_bookings}")
    print(f"   ✓ Bookings existentes: {existing_bookings}")
    print(f"   📊 Total procesado: {created_bookings + existing_bookings}")


def verify_bookings():
    """Verifica que todas las sesiones tengan bookings correctos."""
    
    print("\n🔍 Verificando integridad de bookings...")
    
    sessions_without_bookings = []
    
    for session in ActivitySession.objects.filter(status__in=['SCHEDULED', 'COMPLETED']):
        attendee_count = session.attendees.count()
        booking_count = ActivitySessionBooking.objects.filter(session=session).count()
        
        if attendee_count != booking_count:
            sessions_without_bookings.append({
                'session_id': session.id,
                'activity': session.activity.name,
                'date': session.start_datetime,
                'attendees': attendee_count,
                'bookings': booking_count,
                'missing': attendee_count - booking_count
            })
    
    if sessions_without_bookings:
        print(f"\n⚠️  Encontradas {len(sessions_without_bookings)} sesiones con inconsistencias:")
        for s in sessions_without_bookings[:10]:  # Mostrar primeras 10
            print(f"   - Sesión #{s['session_id']} ({s['activity']}) - {s['date']}")
            print(f"     Asistentes: {s['attendees']}, Bookings: {s['bookings']}, Faltantes: {s['missing']}")
    else:
        print("✅ Todas las sesiones tienen bookings correctos")
    
    return len(sessions_without_bookings) == 0


if __name__ == '__main__':
    import sys
    
    print("=" * 60)
    print("  BACKFILL DE BOOKINGS - Sistema de Asistencias")
    print("=" * 60)
    
    if '--verify-only' in sys.argv:
        verify_bookings()
    else:
        # Confirmación de seguridad
        print("\n⚠️  Este script creará registros de booking para todos los")
        print("   asistentes existentes en sesiones programadas/completadas.")
        print("\n❓ ¿Deseas continuar? (yes/no): ", end='')
        
        confirm = input().strip().lower()
        
        if confirm in ['yes', 'y', 'si', 's']:
            backfill_bookings()
            
            # Verificar resultado
            print("\n" + "=" * 60)
            if verify_bookings():
                print("\n🎉 ¡Proceso completado con éxito!")
            else:
                print("\n⚠️  Algunas inconsistencias detectadas. Revisar arriba.")
        else:
            print("\n❌ Operación cancelada.")
            sys.exit(0)
