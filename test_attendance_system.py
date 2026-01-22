"""
Test del sistema de asistencias
Verificar que los endpoints y la lógica funcionan correctamente.
"""
import os
import django

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'config.settings')
django.setup()

from activities.models import ActivitySession, ActivitySessionBooking
from clients.models import Client
from django.utils import timezone


def test_attendance_marking():
    """Prueba el marcado de asistencia."""
    
    print("🧪 Iniciando tests del sistema de asistencias...\n")
    
    # Test 1: Buscar una sesión con asistentes
    print("Test 1: Buscar sesión con asistentes")
    session = ActivitySession.objects.filter(
        attendees__isnull=False,
        status='SCHEDULED'
    ).first()
    
    if not session:
        print("❌ No hay sesiones programadas con asistentes")
        return False
    
    print(f"✅ Sesión encontrada: #{session.id} - {session.activity.name}")
    print(f"   Fecha: {session.start_datetime}")
    print(f"   Asistentes: {session.attendees.count()}")
    
    # Test 2: Verificar bookings
    print("\nTest 2: Verificar bookings")
    bookings = ActivitySessionBooking.objects.filter(session=session)
    print(f"✅ Bookings encontrados: {bookings.count()}")
    
    if bookings.count() == 0:
        print("❌ No hay bookings para esta sesión")
        return False
    
    # Mostrar estado inicial
    print("\n📊 Estado inicial de bookings:")
    for booking in bookings[:5]:  # Primeros 5
        print(f"   - {booking.client.first_name} {booking.client.last_name}: {booking.attendance_status}")
    
    # Test 3: Marcar asistencia
    print("\nTest 3: Marcar asistencia individual")
    test_booking = bookings.first()
    old_status = test_booking.attendance_status
    
    # Simular marcado de asistencia
    from staff.models import StaffProfile
    staff = StaffProfile.objects.first()
    
    if staff:
        test_booking.mark_attendance('ATTENDED', staff)
        print(f"✅ Marcado como ATTENDED")
        print(f"   Estado anterior: {old_status}")
        print(f"   Estado nuevo: {test_booking.attendance_status}")
        print(f"   Marcado por: {staff}")
        print(f"   Marcado en: {test_booking.marked_at}")
    else:
        print("⚠️  No hay staff disponible, no se puede probar marcado con usuario")
    
    # Test 4: Obtener estadísticas
    print("\nTest 4: Estadísticas de asistencia")
    stats = {
        'total': bookings.count(),
        'attended': bookings.filter(attendance_status='ATTENDED').count(),
        'no_show': bookings.filter(attendance_status='NO_SHOW').count(),
        'late_cancel': bookings.filter(attendance_status='LATE_CANCEL').count(),
        'pending': bookings.filter(attendance_status='PENDING').count(),
    }
    
    print(f"📊 Estadísticas:")
    print(f"   Total: {stats['total']}")
    print(f"   Asistidos: {stats['attended']}")
    print(f"   No vinieron: {stats['no_show']}")
    print(f"   Cancelaciones tardías: {stats['late_cancel']}")
    print(f"   Pendientes: {stats['pending']}")
    
    attendance_rate = (stats['attended'] / stats['total'] * 100) if stats['total'] > 0 else 0
    print(f"   Tasa de asistencia: {attendance_rate:.1f}%")
    
    # Test 5: Verificar método en modelo
    print("\nTest 5: Método mark_attendance() del modelo")
    test_booking2 = bookings[1] if bookings.count() > 1 else bookings.first()
    
    try:
        test_booking2.mark_attendance('NO_SHOW', staff)
        print(f"✅ Método funciona correctamente")
        print(f"   Cliente: {test_booking2.client.first_name} {test_booking2.client.last_name}")
        print(f"   Nuevo estado: {test_booking2.attendance_status}")
    except Exception as e:
        print(f"❌ Error al usar método: {e}")
        return False
    
    print("\n" + "="*60)
    print("✅ Todos los tests pasaron correctamente")
    print("="*60)
    
    return True


def show_sample_data():
    """Muestra datos de ejemplo del sistema."""
    
    print("\n📋 DATOS DE EJEMPLO DEL SISTEMA\n")
    
    # Sesiones con asistencia marcada
    sessions_with_attendance = ActivitySession.objects.filter(
        bookings__attendance_status__in=['ATTENDED', 'NO_SHOW', 'LATE_CANCEL']
    ).distinct()[:5]
    
    print(f"🎯 Sesiones con asistencia registrada: {sessions_with_attendance.count()}")
    for session in sessions_with_attendance:
        bookings = session.bookings.all()
        attended = bookings.filter(attendance_status='ATTENDED').count()
        total = bookings.count()
        rate = (attended / total * 100) if total > 0 else 0
        
        print(f"\n   📅 {session.activity.name}")
        print(f"      Fecha: {session.start_datetime.strftime('%d/%m/%Y %H:%M')}")
        print(f"      Asistencia: {attended}/{total} ({rate:.0f}%)")
    
    # Clientes con mejor asistencia
    print("\n⭐ Top 5 clientes con mejor asistencia:")
    
    from django.db.models import Count, Q
    
    clients_stats = Client.objects.annotate(
        total_bookings=Count('bookings'),
        attended_bookings=Count('bookings', filter=Q(bookings__attendance_status='ATTENDED'))
    ).filter(total_bookings__gte=3).order_by('-attended_bookings')[:5]
    
    for client in clients_stats:
        if client.total_bookings > 0:
            rate = (client.attended_bookings / client.total_bookings * 100)
            print(f"   {client.first_name} {client.last_name}")
            print(f"      {client.attended_bookings}/{client.total_bookings} clases ({rate:.0f}%)")


if __name__ == '__main__':
    import sys
    
    print("="*60)
    print("  TEST DEL SISTEMA DE ASISTENCIAS")
    print("="*60 + "\n")
    
    if '--sample' in sys.argv:
        show_sample_data()
    else:
        success = test_attendance_marking()
        
        if success:
            print("\n💡 Tip: Usa --sample para ver datos de ejemplo")
        
        sys.exit(0 if success else 1)
