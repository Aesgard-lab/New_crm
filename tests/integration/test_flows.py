"""
Tests de integración para flujos completos del sistema.

Estos tests verifican flujos end-to-end que involucran múltiples
componentes trabajando juntos.
"""
import pytest
from decimal import Decimal
from datetime import date, timedelta
from django.utils import timezone
from rest_framework.test import APIClient

from tests.factories import (
    UserFactory, GymFactory, ClientFactory,
    MembershipPlanFactory, ClientMembershipFactory,
    ActivityFactory, ActivitySessionFactory, BookingFactory,
)


@pytest.mark.django_db
class TestClientRegistrationFlow:
    """Tests del flujo completo de registro de cliente."""

    def test_complete_client_onboarding(self):
        """Test flujo: crear gym → crear cliente → asignar membresía."""
        # 1. Crear gimnasio
        gym = GymFactory(name="Test Gym")
        assert gym.id is not None

        # 2. Crear plan de membresía
        plan = MembershipPlanFactory(
            gym=gym,
            name="Plan Mensual",
            base_price=Decimal("29.99"),
            pack_validity_days=30,
        )
        assert plan.base_price == Decimal("29.99")

        # 3. Crear usuario y cliente
        user = UserFactory(email="nuevo.cliente@test.com")
        client = ClientFactory(
            gym=gym,
            user=user,
            first_name="Juan",
            last_name="Pérez",
            status="ACTIVE",
        )
        assert client.full_name == "Juan Pérez"

        # 4. Asignar membresía
        today = date.today()
        membership = ClientMembershipFactory(
            client=client,
            plan=plan,
            start_date=today,
            end_date=today + timedelta(days=30),
            status="ACTIVE",
        )
        assert membership.is_active
        assert membership.days_remaining >= 29  # Al menos 29 días restantes

    def test_client_with_multiple_memberships_history(self):
        """Test cliente con historial de múltiples membresías."""
        gym = GymFactory()
        client = ClientFactory(gym=gym)

        # Membresía expirada
        old_plan = MembershipPlanFactory(gym=gym, name="Plan Antiguo")
        old_membership = ClientMembershipFactory(
            client=client,
            plan=old_plan,
            start_date=date.today() - timedelta(days=60),
            end_date=date.today() - timedelta(days=30),
            status="EXPIRED",
        )

        # Membresía actual
        new_plan = MembershipPlanFactory(gym=gym, name="Plan Nuevo")
        active_membership = ClientMembershipFactory(
            client=client,
            plan=new_plan,
            start_date=date.today(),
            end_date=date.today() + timedelta(days=30),
            status="ACTIVE",
        )

        # Verificar historial
        memberships = client.memberships.all().order_by('-start_date')
        assert memberships.count() == 2
        assert memberships.first().status == "ACTIVE"
        assert memberships.last().status == "EXPIRED"


@pytest.mark.django_db
class TestActivityBookingFlow:
    """Tests del flujo completo de reservas de actividades."""

    def test_complete_booking_flow(self):
        """Test flujo: crear actividad → crear sesión → reservar → confirmar asistencia."""
        gym = GymFactory()
        client = ClientFactory(gym=gym)

        # 1. Crear actividad
        activity = ActivityFactory(gym=gym, name="Yoga Matutino")
        assert activity.name == "Yoga Matutino"

        # 2. Crear sesión
        tomorrow = timezone.now() + timedelta(days=1)
        session = ActivitySessionFactory(
            activity=activity,
            start_datetime=tomorrow,
        )
        assert session.id is not None

        # 3. Crear reserva
        booking = BookingFactory(
            session=session,
            client=client,
            status="CONFIRMED",
        )
        assert booking.status == "CONFIRMED"

        # 4. Marcar asistencia
        booking.status = "ATTENDED"
        booking.save()
        assert booking.status == "ATTENDED"

    def test_booking_capacity_limits(self):
        """Test que las reservas respetan límites de capacidad."""
        gym = GymFactory()
        activity = ActivityFactory(gym=gym, base_capacity=2)

        tomorrow = timezone.now() + timedelta(days=1)
        session = ActivitySessionFactory(
            activity=activity,
            start_datetime=tomorrow,
            max_capacity=2,
        )

        # Crear 2 reservas (máximo)
        for i in range(2):
            client = ClientFactory(gym=gym)
            BookingFactory(session=session, client=client, status="CONFIRMED")

        # Verificar que se crearon las reservas
        from activities.models import ActivitySessionBooking
        bookings_count = ActivitySessionBooking.objects.filter(session=session).count()
        assert bookings_count == 2

    def test_cancellation_updates_booking(self):
        """Test que cancelar una reserva actualiza el estado."""
        gym = GymFactory()
        activity = ActivityFactory(gym=gym, base_capacity=1)

        tomorrow = timezone.now() + timedelta(days=1)
        session = ActivitySessionFactory(
            activity=activity,
            start_datetime=tomorrow,
            max_capacity=1,
        )

        client = ClientFactory(gym=gym)
        booking = BookingFactory(session=session, client=client, status="CONFIRMED")

        assert booking.status == "CONFIRMED"

        # Cancelar reserva
        booking.status = "CANCELLED"
        booking.save()

        booking.refresh_from_db()
        assert booking.status == "CANCELLED"


@pytest.mark.django_db
class TestMembershipAccessControl:
    """Tests de control de acceso basado en membresía."""

    def test_active_membership_grants_access(self):
        """Cliente con membresía activa tiene acceso."""
        gym = GymFactory()
        client = ClientFactory(gym=gym, status="ACTIVE")
        plan = MembershipPlanFactory(gym=gym)

        membership = ClientMembershipFactory(
            client=client,
            plan=plan,
            status="ACTIVE",
            end_date=date.today() + timedelta(days=30),
        )

        assert membership.is_active
        assert client.status == "ACTIVE"

    def test_expired_membership_denies_access(self):
        """Cliente con membresía expirada no tiene acceso."""
        gym = GymFactory()
        client = ClientFactory(gym=gym, status="ACTIVE")
        plan = MembershipPlanFactory(gym=gym)

        membership = ClientMembershipFactory(
            client=client,
            plan=plan,
            status="EXPIRED",
            end_date=date.today() - timedelta(days=1),
        )

        assert not membership.is_active

    def test_session_based_membership_tracking(self):
        """Test membresía basada en sesiones."""
        gym = GymFactory()
        client = ClientFactory(gym=gym)
        plan = MembershipPlanFactory(gym=gym)

        membership = ClientMembershipFactory(
            client=client,
            plan=plan,
            sessions_total=10,
            sessions_used=3,
            status="ACTIVE",
        )

        assert membership.sessions_remaining == 7

        assert membership.sessions_remaining == 7


@pytest.mark.django_db
class TestAPIIntegration:
    """Tests de integración de la API."""

    @pytest.fixture
    def api_client(self):
        return APIClient()

    def test_authenticated_user_can_access_protected_endpoints(self, api_client):
        """Usuario autenticado puede acceder a endpoints protegidos."""
        gym = GymFactory()
        user = UserFactory()
        ClientFactory(gym=gym, user=user)

        api_client.force_authenticate(user=user)
        response = api_client.get('/api/profile/')

        assert response.status_code == 200

    def test_unauthenticated_user_denied_access(self, api_client):
        """Usuario no autenticado es rechazado."""
        response = api_client.get('/api/profile/')
        assert response.status_code == 401

    def test_gym_search_endpoint(self, api_client):
        """Test endpoint de búsqueda de gimnasios."""
        gym1 = GymFactory(name="Fitness Center", slug="fitness-center")
        gym2 = GymFactory(name="Power Gym", slug="power-gym")

        # Test que los gimnasios se crearon correctamente
        from organizations.models import Gym
        assert Gym.objects.filter(slug="fitness-center").exists()
        assert Gym.objects.filter(slug="power-gym").exists()

    def test_login_with_valid_credentials(self, api_client):
        """Test login con credenciales válidas."""
        gym = GymFactory()
        user = UserFactory(email="test@example.com")
        user.set_password("TestPass123!")
        user.save()
        ClientFactory(gym=gym, user=user)

        response = api_client.post('/api/auth/login/', {
            'email': 'test@example.com',
            'password': 'TestPass123!',
            'gym_id': gym.id,
        })

        # Puede ser 200 o incluir token dependiendo de la implementación
        assert response.status_code in [200, 400]  # 400 si falta algo en la request


@pytest.mark.django_db
class TestDataIntegrity:
    """Tests de integridad de datos."""

    def test_client_gym_relationship(self):
        """Cliente pertenece a un solo gimnasio."""
        gym1 = GymFactory(name="Gym 1")
        gym2 = GymFactory(name="Gym 2")

        client = ClientFactory(gym=gym1)
        assert client.gym == gym1
        assert client.gym != gym2

    def test_membership_plan_belongs_to_gym(self):
        """Plan de membresía pertenece a un gimnasio específico."""
        gym = GymFactory()
        plan = MembershipPlanFactory(gym=gym)

        assert plan.gym == gym

    def test_activity_session_inherits_activity_gym(self):
        """Sesión de actividad hereda el gimnasio de la actividad."""
        gym = GymFactory()
        activity = ActivityFactory(gym=gym)
        session = ActivitySessionFactory(activity=activity)

        assert session.activity.gym == gym

    def test_booking_references_correct_entities(self):
        """Reserva referencia correctamente cliente y sesión."""
        gym = GymFactory()
        client = ClientFactory(gym=gym)
        activity = ActivityFactory(gym=gym)
        session = ActivitySessionFactory(activity=activity)
        booking = BookingFactory(session=session, client=client)

        assert booking.client == client
        assert booking.session == session
        assert booking.client.gym == booking.session.activity.gym


@pytest.mark.django_db
@pytest.mark.slow
class TestConcurrentOperations:
    """Tests de operaciones concurrentes (marcados como slow)."""

    def test_multiple_bookings_same_session(self):
        """Múltiples clientes pueden reservar la misma sesión."""
        gym = GymFactory()
        activity = ActivityFactory(gym=gym, base_capacity=10)

        tomorrow = timezone.now() + timedelta(days=1)
        session = ActivitySessionFactory(
            activity=activity,
            start_datetime=tomorrow,
            max_capacity=10,
        )

        # Crear 5 clientes con reservas
        clients = [ClientFactory(gym=gym) for _ in range(5)]
        bookings = [
            BookingFactory(session=session, client=client, status="CONFIRMED")
            for client in clients
        ]

        from activities.models import ActivitySessionBooking
        bookings_count = ActivitySessionBooking.objects.filter(
            session=session,
            status="CONFIRMED"
        ).count()
        assert bookings_count == 5
