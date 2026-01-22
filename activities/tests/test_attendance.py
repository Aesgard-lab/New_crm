"""
Tests para el sistema de asistencias
"""
from django.test import TestCase, Client as TestClient
from django.utils import timezone
from datetime import timedelta
import json

from activities.models import Activity, ActivitySession, ActivitySessionBooking
from clients.models import Client
from organizations.models import Gym
from staff.models import StaffProfile
from django.contrib.auth import get_user_model

User = get_user_model()


class AttendanceSystemTestCase(TestCase):
    """Tests del sistema de marcado de asistencias"""
    
    def setUp(self):
        """Configuración inicial para cada test"""
        # Crear gimnasio
        self.gym = Gym.objects.create(
            name="Test Gym",
            email="test@gym.com"
        )
        
        # Crear usuario y staff
        self.user = User.objects.create_user(
            email='staff@test.com',
            password='testpass123'
        )
        self.user.first_name = 'Test'
        self.user.last_name = 'Staff'
        self.user.save()
        self.staff = StaffProfile.objects.create(
            user=self.user,
            gym=self.gym,
            role='ADMIN'
        )
        
        # Crear actividad
        self.activity = Activity.objects.create(
            gym=self.gym,
            name="Yoga Test",
            duration=60,
            color="#FF5733",
            base_capacity=10
        )
        
        # Crear sesión
        self.session = ActivitySession.objects.create(
            gym=self.gym,
            activity=self.activity,
            start_datetime=timezone.now() + timedelta(hours=2),
            end_datetime=timezone.now() + timedelta(hours=3),
            max_capacity=10,
            status='SCHEDULED'
        )
        
        # Crear clientes de prueba
        self.clients = []
        for i in range(3):
            client = Client.objects.create(
                gym=self.gym,
                first_name=f"Cliente{i}",
                last_name=f"Test{i}",
                email=f"cliente{i}@test.com",
                phone_number=f"+3460000000{i}"
            )
            self.clients.append(client)
            
            # Añadir a la sesión
            self.session.attendees.add(client)
            
            # Crear booking
            ActivitySessionBooking.objects.create(
                session=self.session,
                client=client,
                status='CONFIRMED',
                attendance_status='PENDING'
            )
        
        # Cliente de test client para peticiones HTTP
        self.test_client = TestClient()
    
    def test_booking_creation(self):
        """Test: Se crean bookings correctamente"""
        bookings = ActivitySessionBooking.objects.filter(session=self.session)
        self.assertEqual(bookings.count(), 3)
        
        for booking in bookings:
            self.assertEqual(booking.attendance_status, 'PENDING')
            self.assertEqual(booking.status, 'CONFIRMED')
    
    def test_mark_attendance_method(self):
        """Test: Método mark_attendance() funciona correctamente"""
        booking = ActivitySessionBooking.objects.filter(session=self.session).first()
        
        # Marcar como asistido
        booking.mark_attendance('ATTENDED', self.staff)
        
        # Verificar cambios
        booking.refresh_from_db()
        self.assertEqual(booking.attendance_status, 'ATTENDED')
        self.assertEqual(booking.marked_by, self.staff)
        self.assertIsNotNone(booking.marked_at)
    
    def test_mark_attendance_states(self):
        """Test: Todos los estados de asistencia funcionan"""
        bookings = list(ActivitySessionBooking.objects.filter(session=self.session))
        
        states = ['ATTENDED', 'NO_SHOW', 'LATE_CANCEL']
        
        for i, state in enumerate(states):
            bookings[i].mark_attendance(state, self.staff)
            bookings[i].refresh_from_db()
            self.assertEqual(bookings[i].attendance_status, state)
    
    def test_attendance_api_endpoint_get(self):
        """Test: Endpoint GET de asistencias"""
        self.test_client.force_login(self.user)
        
        response = self.test_client.get(
            f'/activities/api/session/{self.session.id}/attendance/'
        )
        
        self.assertEqual(response.status_code, 200)
        data = json.loads(response.content)
        
        self.assertEqual(data['session_id'], self.session.id)
        self.assertEqual(data['total_bookings'], 3)
        self.assertEqual(data['pending'], 3)
        self.assertEqual(data['attended'], 0)
    
    def test_attendance_api_endpoint_post_single(self):
        """Test: Endpoint POST marca asistencia individual"""
        self.test_client.force_login(self.user)
        
        booking = ActivitySessionBooking.objects.filter(session=self.session).first()
        
        response = self.test_client.post(
            f'/activities/api/session/{self.session.id}/attendance/',
            data=json.dumps({
                'booking_id': booking.id,
                'status': 'ATTENDED'
            }),
            content_type='application/json'
        )
        
        self.assertEqual(response.status_code, 200)
        data = json.loads(response.content)
        
        self.assertEqual(data['status'], 'ok')
        self.assertEqual(data['attendance_status'], 'ATTENDED')
        
        # Verificar en BD
        booking.refresh_from_db()
        self.assertEqual(booking.attendance_status, 'ATTENDED')
    
    def test_attendance_api_endpoint_post_multiple(self):
        """Test: Endpoint POST marca múltiples asistencias"""
        self.test_client.force_login(self.user)
        
        bookings = ActivitySessionBooking.objects.filter(session=self.session)
        booking_ids = [b.id for b in bookings]
        
        response = self.test_client.post(
            f'/activities/api/session/{self.session.id}/attendance/',
            data=json.dumps({
                'booking_ids': booking_ids,
                'status': 'ATTENDED'
            }),
            content_type='application/json'
        )
        
        self.assertEqual(response.status_code, 200)
        data = json.loads(response.content)
        
        self.assertEqual(data['status'], 'ok')
        self.assertEqual(data['updated'], 3)
        
        # Verificar todos están marcados
        for booking in bookings:
            booking.refresh_from_db()
            self.assertEqual(booking.attendance_status, 'ATTENDED')
    
    def test_session_detail_includes_attendance(self):
        """Test: Detalle de sesión incluye datos de asistencia"""
        self.test_client.force_login(self.user)
        
        # Marcar algunas asistencias
        bookings = list(ActivitySessionBooking.objects.filter(session=self.session))
        bookings[0].mark_attendance('ATTENDED', self.staff)
        bookings[1].mark_attendance('NO_SHOW', self.staff)
        
        response = self.test_client.get(
            f'/activities/api/session/{self.session.id}/'
        )
        
        self.assertEqual(response.status_code, 200)
        data = json.loads(response.content)
        
        # Verificar que incluye datos de asistencia
        self.assertIn('attendees', data)
        self.assertEqual(len(data['attendees']), 3)
        
        # Verificar que cada asistente tiene booking_id y attendance_status
        for attendee in data['attendees']:
            self.assertIn('booking_id', attendee)
            self.assertIn('attendance_status', attendee)
    
    def test_attendance_statistics(self):
        """Test: Estadísticas de asistencia se calculan correctamente"""
        bookings = list(ActivitySessionBooking.objects.filter(session=self.session))
        
        # Marcar diferentes estados
        bookings[0].mark_attendance('ATTENDED', self.staff)
        bookings[1].mark_attendance('ATTENDED', self.staff)
        bookings[2].mark_attendance('NO_SHOW', self.staff)
        
        self.test_client.force_login(self.user)
        response = self.test_client.get(
            f'/activities/api/session/{self.session.id}/attendance/'
        )
        
        data = json.loads(response.content)
        
        self.assertEqual(data['total_bookings'], 3)
        self.assertEqual(data['attended'], 2)
        self.assertEqual(data['no_show'], 1)
        self.assertEqual(data['late_cancel'], 0)
        self.assertEqual(data['pending'], 0)
        self.assertEqual(data['attendance_rate'], 66.67)  # 2/3 * 100
    
    def test_booking_created_on_add_attendee(self):
        """Test: Se crea booking automáticamente al añadir asistente"""
        # Crear nuevo cliente
        new_client = Client.objects.create(
            gym=self.gym,
            first_name="Nuevo",
            last_name="Cliente",
            email="nuevo@test.com"
        )
        
        self.test_client.force_login(self.user)
        
        # Añadir a sesión vía API
        response = self.test_client.post(
            f'/activities/api/session/{self.session.id}/attendees/',
            data=json.dumps({'client_id': new_client.id}),
            content_type='application/json'
        )
        
        self.assertEqual(response.status_code, 200)
        
        # Verificar que se creó el booking
        booking = ActivitySessionBooking.objects.filter(
            session=self.session,
            client=new_client
        ).first()
        
        self.assertIsNotNone(booking)
        self.assertEqual(booking.attendance_status, 'PENDING')
        self.assertEqual(booking.status, 'CONFIRMED')
    
    def test_invalid_status_rejected(self):
        """Test: Estados inválidos son rechazados"""
        booking = ActivitySessionBooking.objects.filter(session=self.session).first()
        
        self.test_client.force_login(self.user)
        
        response = self.test_client.post(
            f'/activities/api/session/{self.session.id}/attendance/',
            data=json.dumps({
                'booking_id': booking.id,
                'status': 'INVALID_STATUS'
            }),
            content_type='application/json'
        )
        
        self.assertEqual(response.status_code, 400)
        data = json.loads(response.content)
        self.assertIn('error', data)


class AttendanceIntegrationTestCase(TestCase):
    """Tests de integración del sistema de asistencias"""
    
    def setUp(self):
        """Configuración inicial"""
        self.gym = Gym.objects.create(
            name="Integration Test Gym",
            email="integration@test.com"
        )
        
        self.user = User.objects.create_user(
            email='intstaff@test.com',
            password='testpass123'
        )
        self.user.first_name = 'Int'
        self.user.last_name = 'Staff'
        self.user.save()
        self.staff = StaffProfile.objects.create(
            user=self.user,
            gym=self.gym,
            role='ADMIN'
        )
        
        self.activity = Activity.objects.create(
            gym=self.gym,
            name="Pilates Integration",
            duration=45,
            base_capacity=5
        )
        
        self.test_client = TestClient()
    
    def test_full_attendance_flow(self):
        """Test: Flujo completo de asistencia"""
        # 1. Crear sesión
        session = ActivitySession.objects.create(
            gym=self.gym,
            activity=self.activity,
            start_datetime=timezone.now() + timedelta(hours=1),
            end_datetime=timezone.now() + timedelta(hours=2),
            max_capacity=5
        )
        
        # 2. Añadir clientes
        clients = []
        for i in range(5):
            client = Client.objects.create(
                gym=self.gym,
                first_name=f"Flow{i}",
                last_name="Test",
                email=f"flow{i}@test.com"
            )
            clients.append(client)
            session.attendees.add(client)
            
            # Simular creación automática de booking
            ActivitySessionBooking.objects.create(
                session=session,
                client=client,
                status='CONFIRMED',
                attendance_status='PENDING'
            )
        
        # 3. Verificar estado inicial
        self.assertEqual(session.attendees.count(), 5)
        self.assertEqual(
            ActivitySessionBooking.objects.filter(
                session=session,
                attendance_status='PENDING'
            ).count(),
            5
        )
        
        # 4. Marcar asistencias (3 asistieron, 1 no vino, 1 canceló tarde)
        bookings = list(ActivitySessionBooking.objects.filter(session=session))
        
        bookings[0].mark_attendance('ATTENDED', self.staff)
        bookings[1].mark_attendance('ATTENDED', self.staff)
        bookings[2].mark_attendance('ATTENDED', self.staff)
        bookings[3].mark_attendance('NO_SHOW', self.staff)
        bookings[4].mark_attendance('LATE_CANCEL', self.staff)
        
        # 5. Verificar estadísticas finales
        self.test_client.force_login(self.user)
        response = self.test_client.get(
            f'/activities/api/session/{session.id}/attendance/'
        )
        
        data = json.loads(response.content)
        
        self.assertEqual(data['attended'], 3)
        self.assertEqual(data['no_show'], 1)
        self.assertEqual(data['late_cancel'], 1)
        self.assertEqual(data['pending'], 0)
        self.assertEqual(data['attendance_rate'], 60.0)  # 3/5 * 100


def run_tests():
    """Ejecuta todos los tests y muestra resumen"""
    import sys
    from io import StringIO
    from django.test.runner import DiscoverRunner
    
    # Capturar salida
    old_stdout = sys.stdout
    sys.stdout = StringIO()
    
    # Ejecutar tests
    runner = DiscoverRunner(verbosity=2)
    failures = runner.run_tests(['activities.tests.test_attendance'])
    
    # Restaurar stdout
    output = sys.stdout.getvalue()
    sys.stdout = old_stdout
    
    print(output)
    
    return failures == 0
