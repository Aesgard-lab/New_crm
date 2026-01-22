"""
Tests para el sistema de check-in QR de clases grupales.
"""
import time
from datetime import timedelta

from django.test import TestCase, Client as HttpClient
from django.utils import timezone
from django.contrib.auth import get_user_model

from activities.models import (
    Activity, ActivitySession, 
    AttendanceSettings, SessionCheckin
)
from activities.checkin_views import generate_qr_token, verify_qr_token
from clients.models import Client as ClientModel
from organizations.models import Gym, Franchise

User = get_user_model()


class AttendanceSettingsModelTest(TestCase):
    """Tests para el modelo AttendanceSettings."""
    
    def setUp(self):
        self.franchise = Franchise.objects.create(name='Test Franchise')
        self.gym = Gym.objects.create(
            name='Test Gym',
            franchise=self.franchise
        )
    
    def test_create_default_settings(self):
        """Crear configuración por defecto."""
        settings_obj = AttendanceSettings.objects.create(
            gym=self.gym,
            checkin_mode='STAFF_ONLY'
        )
        
        self.assertEqual(settings_obj.gym, self.gym)
        self.assertEqual(settings_obj.qr_refresh_seconds, 30)
        self.assertEqual(settings_obj.qr_checkin_minutes_before, 15)
        self.assertEqual(settings_obj.qr_checkin_minutes_after, 30)
    
    def test_get_or_create_settings(self):
        """get_or_create debe funcionar correctamente."""
        # Crear
        settings_obj, created = AttendanceSettings.objects.get_or_create(
            gym=self.gym,
            defaults={'checkin_mode': 'QR_ENABLED'}
        )
        
        self.assertTrue(created)
        self.assertEqual(settings_obj.checkin_mode, 'QR_ENABLED')
        
        # Obtener existente
        settings_obj2, created2 = AttendanceSettings.objects.get_or_create(
            gym=self.gym,
            defaults={'checkin_mode': 'BOTH'}
        )
        
        self.assertFalse(created2)
        self.assertEqual(settings_obj2.checkin_mode, 'QR_ENABLED')
    
    def test_default_values(self):
        """Verificar valores por defecto."""
        settings_obj = AttendanceSettings.objects.create(gym=self.gym)
        
        self.assertEqual(settings_obj.qr_refresh_seconds, 30)
        self.assertEqual(settings_obj.qr_checkin_minutes_before, 15)
        self.assertEqual(settings_obj.qr_checkin_minutes_after, 30)
        self.assertEqual(settings_obj.checkin_mode, 'STAFF_ONLY')
    
    def test_checkin_mode_choices(self):
        """Verificar las opciones de modo de check-in."""
        modes = [choice[0] for choice in AttendanceSettings.CHECKIN_MODE_CHOICES]
        
        self.assertIn('STAFF_ONLY', modes)
        self.assertIn('QR_ENABLED', modes)
        self.assertIn('BOTH', modes)


class SessionCheckinModelTest(TestCase):
    """Tests para el modelo SessionCheckin."""
    
    def setUp(self):
        self.franchise = Franchise.objects.create(name='Checkin Test Franchise')
        self.gym = Gym.objects.create(
            name='Checkin Test Gym',
            franchise=self.franchise
        )
        
        # User model usa email, no username
        self.client_user = User.objects.create_user(
            email='client_checkin@test.com',
            password='testpass123'
        )
        self.client_obj = ClientModel.objects.create(
            user=self.client_user,
            gym=self.gym,
            first_name='Test',
            last_name='Client'
        )
        
        self.activity = Activity.objects.create(
            name='Yoga Test',
            gym=self.gym,
            duration=60,
            base_capacity=20,
            qr_checkin_enabled=True
        )
        
        start = timezone.now() + timedelta(minutes=10)
        self.session = ActivitySession.objects.create(
            activity=self.activity,
            gym=self.gym,
            start_datetime=start,
            end_datetime=start + timedelta(minutes=self.activity.duration),
            max_capacity=20
        )
    
    def test_create_checkin(self):
        """Crear un check-in válido."""
        checkin = SessionCheckin.objects.create(
            session=self.session,
            client=self.client_obj,
            method='QR'
        )
        
        self.assertIsNotNone(checkin.checked_in_at)
        self.assertEqual(checkin.session, self.session)
        self.assertEqual(checkin.client, self.client_obj)
        self.assertEqual(checkin.method, 'QR')
    
    def test_unique_session_client(self):
        """No se puede hacer doble check-in del mismo cliente en la misma sesión."""
        SessionCheckin.objects.create(
            session=self.session,
            client=self.client_obj,
            method='QR'
        )
        
        from django.db import IntegrityError
        with self.assertRaises(IntegrityError):
            SessionCheckin.objects.create(
                session=self.session,
                client=self.client_obj,
                method='STAFF'
            )
    
    def test_checkin_method_choices(self):
        """Verificar las opciones de método de check-in."""
        methods = [choice[0] for choice in SessionCheckin.CHECKIN_METHOD_CHOICES]
        
        self.assertIn('STAFF', methods)
        self.assertIn('QR', methods)
        self.assertIn('APP', methods)


class QRTokenGenerationTest(TestCase):
    """Tests para generación y verificación de tokens QR."""
    
    def setUp(self):
        self.franchise = Franchise.objects.create(name='Token Test Franchise')
        self.gym = Gym.objects.create(
            name='Token Test Gym',
            franchise=self.franchise
        )
        
        self.activity = Activity.objects.create(
            name='Spinning Test',
            gym=self.gym,
            duration=45,
            base_capacity=15,
            qr_checkin_enabled=True
        )
        start = timezone.now() + timedelta(minutes=30)
        self.session = ActivitySession.objects.create(
            activity=self.activity,
            gym=self.gym,
            start_datetime=start,
            end_datetime=start + timedelta(minutes=self.activity.duration),
            max_capacity=15
        )
    
    def test_generate_qr_token_format(self):
        """Token debe tener formato correcto: SESSION_ID:TIMESTAMP:SIGNATURE."""
        current_time = int(time.time())
        token = generate_qr_token(self.session.id, current_time)
        parts = token.split(':')
        
        self.assertEqual(len(parts), 3)
        self.assertEqual(int(parts[0]), self.session.id)
        
        # El timestamp debe ser un entero válido
        timestamp = int(parts[1])
        self.assertEqual(timestamp, current_time)
        
        # La firma debe ser hex (16 caracteres)
        self.assertEqual(len(parts[2]), 16)
        self.assertTrue(all(c in '0123456789abcdef' for c in parts[2]))
    
    def test_verify_valid_token(self):
        """Token válido debe verificarse correctamente."""
        current_time = int(time.time())
        token = generate_qr_token(self.session.id, current_time)
        result = verify_qr_token(token, self.session.id, max_age_seconds=300)
        
        self.assertTrue(result)
    
    def test_verify_expired_token(self):
        """Token expirado debe ser rechazado."""
        # Crear token con timestamp antiguo
        old_timestamp = int((timezone.now() - timedelta(hours=1)).timestamp())
        token = generate_qr_token(self.session.id, old_timestamp)
        
        result = verify_qr_token(token, self.session.id, max_age_seconds=30)
        
        self.assertFalse(result)
    
    def test_verify_invalid_signature(self):
        """Token con firma inválida debe ser rechazado."""
        timestamp = int(time.time())
        invalid_token = f"{self.session.id}:{timestamp}:invalidsignature"
        
        result = verify_qr_token(invalid_token, self.session.id)
        
        self.assertFalse(result)
    
    def test_verify_wrong_session_id(self):
        """Token para otra sesión debe ser rechazado."""
        current_time = int(time.time())
        token = generate_qr_token(self.session.id, current_time)
        
        # Verificar con session_id diferente
        result = verify_qr_token(token, self.session.id + 999, max_age_seconds=300)
        
        self.assertFalse(result)
    
    def test_verify_malformed_token(self):
        """Token mal formado debe ser rechazado."""
        malformed_tokens = [
            'notavalidtoken',
            '123:abc',
            '123',
            '',
            ':::',
        ]
        
        for token in malformed_tokens:
            result = verify_qr_token(token, self.session.id)
            self.assertFalse(result, f"Token '{token}' debería ser inválido")
    
    def test_token_regeneration_changes_with_time(self):
        """Tokens generados en diferentes momentos son diferentes."""
        time1 = int(time.time())
        time2 = time1 + 30  # 30 segundos después
        
        token1 = generate_qr_token(self.session.id, time1)
        token2 = generate_qr_token(self.session.id, time2)
        
        self.assertNotEqual(token1, token2)
    
    def test_same_timestamp_same_token(self):
        """Mismo timestamp genera el mismo token."""
        timestamp = int(time.time())
        
        token1 = generate_qr_token(self.session.id, timestamp)
        token2 = generate_qr_token(self.session.id, timestamp)
        
        self.assertEqual(token1, token2)


class ActivityQRToggleTest(TestCase):
    """Tests para el toggle de QR check-in por actividad."""
    
    def setUp(self):
        self.franchise = Franchise.objects.create(name='Toggle Test Franchise')
        self.gym = Gym.objects.create(
            name='Toggle Test Gym',
            franchise=self.franchise
        )
    
    def test_activity_qr_disabled_by_default(self):
        """Las nuevas actividades tienen QR deshabilitado por defecto."""
        activity = Activity.objects.create(
            name='Nueva Actividad',
            gym=self.gym,
            duration=60,
            base_capacity=20
        )
        
        self.assertFalse(activity.qr_checkin_enabled)
    
    def test_toggle_qr_on_activity(self):
        """Se puede desactivar QR en una actividad."""
        activity = Activity.objects.create(
            name='Actividad Toggle',
            gym=self.gym,
            duration=60,
            base_capacity=20,
            qr_checkin_enabled=True
        )
        
        activity.qr_checkin_enabled = False
        activity.save()
        
        activity.refresh_from_db()
        self.assertFalse(activity.qr_checkin_enabled)
    
    def test_qr_disabled_activity(self):
        """Una actividad puede ser creada con QR deshabilitado."""
        activity = Activity.objects.create(
            name='Actividad Sin QR',
            gym=self.gym,
            duration=45,
            base_capacity=15,
            qr_checkin_enabled=False
        )
        
        self.assertFalse(activity.qr_checkin_enabled)


class QRSecurityTest(TestCase):
    """Tests de seguridad para tokens QR."""
    
    def setUp(self):
        self.franchise = Franchise.objects.create(name='Security Test Franchise')
        self.gym = Gym.objects.create(
            name='Security Test Gym',
            franchise=self.franchise
        )
        
        self.activity = Activity.objects.create(
            name='Security Test Activity',
            gym=self.gym,
            duration=60,
            base_capacity=20,
            qr_checkin_enabled=True
        )
        
        start1 = timezone.now() + timedelta(hours=1)
        self.session1 = ActivitySession.objects.create(
            activity=self.activity,
            gym=self.gym,
            start_datetime=start1,
            end_datetime=start1 + timedelta(minutes=self.activity.duration),
            max_capacity=20
        )
        
        start2 = timezone.now() + timedelta(hours=2)
        self.session2 = ActivitySession.objects.create(
            activity=self.activity,
            gym=self.gym,
            start_datetime=start2,
            end_datetime=start2 + timedelta(minutes=self.activity.duration),
            max_capacity=20
        )
    
    def test_token_session_bound(self):
        """Token solo es válido para la sesión específica."""
        current_time = int(time.time())
        token_session1 = generate_qr_token(self.session1.id, current_time)
        
        # Verificar para sesión correcta
        self.assertTrue(verify_qr_token(token_session1, self.session1.id, max_age_seconds=300))
        
        # Verificar para sesión incorrecta
        self.assertFalse(verify_qr_token(token_session1, self.session2.id, max_age_seconds=300))
    
    def test_expired_token_rejected(self):
        """Tokens expirados son rechazados."""
        # Token de hace 2 minutos
        old_time = int(time.time()) - 120
        old_token = generate_qr_token(self.session1.id, old_time)
        
        # Con ventana de 60 segundos, debe fallar
        self.assertFalse(verify_qr_token(old_token, self.session1.id, max_age_seconds=60))
        
        # Con ventana de 300 segundos, debe pasar
        self.assertTrue(verify_qr_token(old_token, self.session1.id, max_age_seconds=300))
    
    def test_tampered_token_rejected(self):
        """Tokens manipulados son rechazados."""
        current_time = int(time.time())
        valid_token = generate_qr_token(self.session1.id, current_time)
        parts = valid_token.split(':')
        
        # Cambiar session_id
        tampered_token1 = f"999:{parts[1]}:{parts[2]}"
        self.assertFalse(verify_qr_token(tampered_token1, 999, max_age_seconds=300))
        
        # Cambiar timestamp
        tampered_token2 = f"{parts[0]}:1234567890:{parts[2]}"
        self.assertFalse(verify_qr_token(tampered_token2, self.session1.id, max_age_seconds=300))
        
        # Cambiar firma
        tampered_token3 = f"{parts[0]}:{parts[1]}:0000000000000000"
        self.assertFalse(verify_qr_token(tampered_token3, self.session1.id, max_age_seconds=300))


class CheckinWindowTest(TestCase):
    """Tests para la ventana de tiempo de check-in."""
    
    def setUp(self):
        self.franchise = Franchise.objects.create(name='Window Test Franchise')
        self.gym = Gym.objects.create(
            name='Window Test Gym',
            franchise=self.franchise
        )
        
        # Configurar ventana: 15 min antes, 30 min después
        AttendanceSettings.objects.create(
            gym=self.gym,
            checkin_mode='QR_ENABLED',
            qr_checkin_minutes_before=15,
            qr_checkin_minutes_after=30
        )
        
        self.activity = Activity.objects.create(
            name='Window Test Activity',
            gym=self.gym,
            duration=60,
            base_capacity=20,
            qr_checkin_enabled=True
        )
    
    def test_session_starting_soon_in_window(self):
        """Sesión que comienza en 10 minutos está dentro de la ventana."""
        start = timezone.now() + timedelta(minutes=10)
        session = ActivitySession.objects.create(
            activity=self.activity,
            gym=self.gym,
            start_datetime=start,
            end_datetime=start + timedelta(minutes=self.activity.duration),
            max_capacity=20
        )
        
        settings_obj = self.gym.attendance_settings
        now = timezone.now()
        window_start = session.start_datetime - timedelta(minutes=settings_obj.qr_checkin_minutes_before)
        window_end = session.start_datetime + timedelta(minutes=settings_obj.qr_checkin_minutes_after)
        
        self.assertLessEqual(window_start, now)
        self.assertGreaterEqual(window_end, now)
    
    def test_session_too_early_outside_window(self):
        """Sesión que comienza en 2 horas está fuera de la ventana."""
        start = timezone.now() + timedelta(hours=2)
        session = ActivitySession.objects.create(
            activity=self.activity,
            gym=self.gym,
            start_datetime=start,
            end_datetime=start + timedelta(minutes=self.activity.duration),
            max_capacity=20
        )
        
        settings_obj = self.gym.attendance_settings
        now = timezone.now()
        window_start = session.start_datetime - timedelta(minutes=settings_obj.qr_checkin_minutes_before)
        
        # El momento actual debe ser antes del inicio de la ventana
        self.assertGreater(window_start, now)
    
    def test_session_ended_outside_window(self):
        """Sesión que terminó hace 1 hora está fuera de la ventana."""
        start = timezone.now() - timedelta(hours=1)
        session = ActivitySession.objects.create(
            activity=self.activity,
            gym=self.gym,
            start_datetime=start,
            end_datetime=start + timedelta(minutes=self.activity.duration),
            max_capacity=20
        )
        
        settings_obj = self.gym.attendance_settings
        now = timezone.now()
        window_end = session.start_datetime + timedelta(minutes=settings_obj.qr_checkin_minutes_after)
        
        # El momento actual debe ser después del fin de la ventana
        self.assertGreater(now, window_end)


class SessionCheckinRecordTest(TestCase):
    """Tests para los registros de check-in."""
    
    def setUp(self):
        self.franchise = Franchise.objects.create(name='Record Test Franchise')
        self.gym = Gym.objects.create(
            name='Record Test Gym',
            franchise=self.franchise
        )
        
        self.client_user1 = User.objects.create_user(
            email='client_record_1@test.com',
            password='pass1'
        )
        self.client_user2 = User.objects.create_user(
            email='client_record_2@test.com',
            password='pass2'
        )
        
        self.client1 = ClientModel.objects.create(
            user=self.client_user1,
            gym=self.gym,
            first_name='Client',
            last_name='One'
        )
        self.client2 = ClientModel.objects.create(
            user=self.client_user2,
            gym=self.gym,
            first_name='Client',
            last_name='Two'
        )
        
        self.activity = Activity.objects.create(
            name='Record Test Activity',
            gym=self.gym,
            duration=45,
            base_capacity=20,
            qr_checkin_enabled=True
        )
        
        start = timezone.now() + timedelta(minutes=10)
        self.session = ActivitySession.objects.create(
            activity=self.activity,
            gym=self.gym,
            start_datetime=start,
            end_datetime=start + timedelta(minutes=self.activity.duration),
            max_capacity=20
        )
    
    def test_multiple_clients_same_session(self):
        """Múltiples clientes pueden hacer check-in en la misma sesión."""
        SessionCheckin.objects.create(
            session=self.session,
            client=self.client1,
            method='QR'
        )
        SessionCheckin.objects.create(
            session=self.session,
            client=self.client2,
            method='QR'
        )
        
        self.assertEqual(SessionCheckin.objects.filter(session=self.session).count(), 2)
    
    def test_checkin_stores_ip(self):
        """Check-in puede almacenar la IP del cliente."""
        checkin = SessionCheckin.objects.create(
            session=self.session,
            client=self.client1,
            method='QR',
            ip_address='192.168.1.100'
        )
        
        self.assertEqual(checkin.ip_address, '192.168.1.100')
    
    def test_checkin_stores_qr_token(self):
        """Check-in puede almacenar el token QR usado."""
        token = generate_qr_token(self.session.id, int(time.time()))
        
        checkin = SessionCheckin.objects.create(
            session=self.session,
            client=self.client1,
            method='QR',
            qr_token=token
        )
        
        self.assertEqual(checkin.qr_token, token)
    
    def test_checkin_auto_timestamp(self):
        """Check-in obtiene timestamp automático."""
        before = timezone.now()
        
        checkin = SessionCheckin.objects.create(
            session=self.session,
            client=self.client1,
            method='QR'
        )
        
        after = timezone.now()
        
        self.assertGreaterEqual(checkin.checked_in_at, before)
        self.assertLessEqual(checkin.checked_in_at, after)


class AttendanceSettingsIntegrationTest(TestCase):
    """Tests de integración para configuración de asistencias."""
    
    def setUp(self):
        self.franchise = Franchise.objects.create(name='Integration Franchise')
        self.gym = Gym.objects.create(
            name='Integration Gym',
            franchise=self.franchise
        )
    
    def test_settings_cascade_on_gym_delete(self):
        """Configuración se elimina cuando se elimina el gym."""
        # Crear nuevo gym para este test
        new_gym = Gym.objects.create(
            name='Gym To Delete',
            franchise=self.franchise
        )
        
        settings_obj = AttendanceSettings.objects.create(gym=new_gym)
        settings_id = settings_obj.id
        
        # Eliminar gym
        new_gym.delete()
        
        # Verificar que settings fue eliminado
        self.assertFalse(AttendanceSettings.objects.filter(id=settings_id).exists())
    
    def test_one_settings_per_gym(self):
        """Solo puede haber una configuración por gym."""
        AttendanceSettings.objects.create(gym=self.gym)
        
        from django.db import IntegrityError
        with self.assertRaises(IntegrityError):
            AttendanceSettings.objects.create(gym=self.gym)
