"""
Tests para el servicio de clientes.

Verifica la lógica de negocio encapsulada en ClientService.
"""
import pytest
from datetime import date, timedelta
from decimal import Decimal

from clients.services import (
    ClientService,
    ClientBulkService,
    ClientCreateData,
    MembershipAssignData,
)
from core.exception_handler import BusinessLogicError, ResourceNotFoundError
from tests.factories import (
    GymFactory,
    ClientFactory,
    MembershipPlanFactory,
    ClientMembershipFactory,
)


@pytest.mark.django_db
class TestClientService:
    """Tests para ClientService."""

    @pytest.fixture
    def gym(self):
        return GymFactory()

    @pytest.fixture
    def service(self, gym):
        return ClientService(gym)

    def test_get_client_success(self, service, gym):
        """Obtener cliente existente."""
        client = ClientFactory(gym=gym)
        result = service.get_client(client.id)
        assert result == client

    def test_get_client_not_found(self, service):
        """Error al obtener cliente inexistente."""
        with pytest.raises(ResourceNotFoundError) as exc:
            service.get_client(99999)
        assert "Cliente" in str(exc.value.message)

    def test_get_client_wrong_gym(self, service):
        """No puede obtener cliente de otro gimnasio."""
        other_gym = GymFactory()
        client = ClientFactory(gym=other_gym)

        with pytest.raises(ResourceNotFoundError):
            service.get_client(client.id)

    def test_list_clients(self, service, gym):
        """Listar clientes del gimnasio."""
        ClientFactory.create_batch(3, gym=gym)
        ClientFactory(gym=GymFactory())  # Otro gym

        clients = service.list_clients()
        assert clients.count() == 3

    def test_list_clients_filter_status(self, service, gym):
        """Filtrar clientes por estado."""
        ClientFactory.create_batch(2, gym=gym, status="ACTIVE")
        ClientFactory(gym=gym, status="INACTIVE")

        active = service.list_clients(status="ACTIVE")
        assert active.count() == 2

    def test_list_clients_search(self, service, gym):
        """Buscar clientes por nombre."""
        ClientFactory(gym=gym, first_name="Juan", last_name="García")
        ClientFactory(gym=gym, first_name="María", last_name="López")

        results = service.list_clients(search="Juan")
        assert results.count() == 1
        assert results.first().first_name == "Juan"

    def test_create_client(self, service):
        """Crear cliente correctamente."""
        data = ClientCreateData(
            first_name="Test",
            last_name="User",
            email="test@example.com",
        )

        client = service.create_client(data)

        assert client.id is not None
        assert client.first_name == "Test"
        assert client.email == "test@example.com"

    def test_create_client_duplicate_email(self, service, gym):
        """Error al crear cliente con email duplicado."""
        ClientFactory(gym=gym, email="existing@example.com")

        data = ClientCreateData(
            first_name="Test",
            last_name="User",
            email="existing@example.com",
        )

        with pytest.raises(BusinessLogicError) as exc:
            service.create_client(data)
        assert "DUPLICATE_EMAIL" == exc.value.code

    def test_create_client_duplicate_dni(self, service, gym):
        """Error al crear cliente con DNI duplicado."""
        ClientFactory(gym=gym, dni="12345678A")

        data = ClientCreateData(
            first_name="Test",
            last_name="User",
            dni="12345678A",
        )

        with pytest.raises(BusinessLogicError) as exc:
            service.create_client(data)
        assert "DUPLICATE_DNI" == exc.value.code

    def test_update_client(self, service, gym):
        """Actualizar cliente."""
        client = ClientFactory(gym=gym, first_name="Old")

        updated = service.update_client(client.id, first_name="New")

        assert updated.first_name == "New"

    def test_update_client_duplicate_email(self, service, gym):
        """Error al actualizar con email duplicado."""
        ClientFactory(gym=gym, email="taken@example.com")
        client = ClientFactory(gym=gym, email="original@example.com")

        with pytest.raises(BusinessLogicError):
            service.update_client(client.id, email="taken@example.com")

    def test_activate_client(self, service, gym):
        """Activar cliente inactivo."""
        client = ClientFactory(gym=gym, status="INACTIVE")

        service.activate_client(client.id)

        client.refresh_from_db()
        assert client.status == "ACTIVE"

    def test_deactivate_client(self, service, gym):
        """Desactivar cliente activo."""
        client = ClientFactory(gym=gym, status="ACTIVE")

        service.deactivate_client(client.id)

        client.refresh_from_db()
        assert client.status == "INACTIVE"


@pytest.mark.django_db
class TestClientServiceMemberships:
    """Tests para gestión de membresías en ClientService."""

    @pytest.fixture
    def gym(self):
        return GymFactory()

    @pytest.fixture
    def service(self, gym):
        return ClientService(gym)

    @pytest.fixture
    def plan(self, gym):
        return MembershipPlanFactory(gym=gym, pack_validity_days=30)

    def test_assign_membership(self, service, gym, plan):
        """Asignar membresía a cliente."""
        client = ClientFactory(gym=gym, status="LEAD")

        data = MembershipAssignData(
            plan_id=plan.id,
            start_date=date.today(),
        )

        membership = service.assign_membership(client.id, data)

        assert membership.id is not None
        assert membership.status == "ACTIVE"
        # La fecha de fin depende de pack_validity_days o frequency
        assert membership.end_date is not None

        # Cliente debería activarse
        client.refresh_from_db()
        assert client.status == "ACTIVE"

    def test_assign_membership_already_active(self, service, gym, plan):
        """Error si cliente ya tiene membresía activa."""
        client = ClientFactory(gym=gym)
        ClientMembershipFactory(client=client, plan=plan, status="ACTIVE")

        data = MembershipAssignData(
            plan_id=plan.id,
            start_date=date.today(),
        )

        with pytest.raises(BusinessLogicError) as exc:
            service.assign_membership(client.id, data)
        assert "ACTIVE_MEMBERSHIP_EXISTS" == exc.value.code

    def test_assign_membership_invalid_plan(self, service, gym):
        """Error con plan inexistente."""
        client = ClientFactory(gym=gym)

        data = MembershipAssignData(
            plan_id=99999,
            start_date=date.today(),
        )

        with pytest.raises(ResourceNotFoundError):
            service.assign_membership(client.id, data)

    def test_get_active_membership(self, service, gym, plan):
        """Obtener membresía activa."""
        client = ClientFactory(gym=gym)
        membership = ClientMembershipFactory(
            client=client, plan=plan, status="ACTIVE"
        )

        result = service.get_active_membership(client.id)

        assert result == membership

    def test_get_active_membership_none(self, service, gym):
        """Sin membresía activa retorna None."""
        client = ClientFactory(gym=gym)

        result = service.get_active_membership(client.id)

        assert result is None

    def test_get_membership_history(self, service, gym, plan):
        """Historial de membresías ordenado."""
        client = ClientFactory(gym=gym)

        old = ClientMembershipFactory(
            client=client,
            plan=plan,
            start_date=date.today() - timedelta(days=60),
            status="EXPIRED",
        )
        new = ClientMembershipFactory(
            client=client,
            plan=plan,
            start_date=date.today(),
            status="ACTIVE",
        )

        history = service.get_membership_history(client.id)

        assert history.count() == 2
        assert history.first() == new  # Más reciente primero


@pytest.mark.django_db
class TestClientServiceStatistics:
    """Tests para estadísticas de clientes."""

    @pytest.fixture
    def gym(self):
        return GymFactory()

    @pytest.fixture
    def service(self, gym):
        return ClientService(gym)

    def test_get_statistics(self, service, gym):
        """Obtener estadísticas de cliente."""
        client = ClientFactory(gym=gym)

        stats = service.get_statistics(client.id)

        assert 'total_bookings' in stats
        assert 'attendance_rate' in stats
        assert 'member_since' in stats


@pytest.mark.django_db
class TestClientBulkService:
    """Tests para operaciones masivas."""

    @pytest.fixture
    def gym(self):
        return GymFactory()

    @pytest.fixture
    def bulk_service(self, gym):
        return ClientBulkService(gym)

    def test_bulk_update_status(self, bulk_service, gym):
        """Actualizar estado de múltiples clientes."""
        clients = ClientFactory.create_batch(3, gym=gym, status="ACTIVE")
        client_ids = [c.id for c in clients]

        result = bulk_service.bulk_update_status(client_ids, "INACTIVE")

        assert result['updated'] == 3

        from clients.models import Client
        for client_id in client_ids:
            client = Client.objects.get(id=client_id)
            assert client.status == "INACTIVE"

    def test_bulk_update_invalid_status(self, bulk_service):
        """Error con estado inválido."""
        with pytest.raises(BusinessLogicError) as exc:
            bulk_service.bulk_update_status([1, 2, 3], "INVALID")
        assert "INVALID_STATUS" == exc.value.code

    def test_expire_memberships(self, bulk_service, gym):
        """Expirar membresías vencidas."""
        plan = MembershipPlanFactory(gym=gym)

        # Membresía vencida
        client1 = ClientFactory(gym=gym)
        ClientMembershipFactory(
            client=client1,
            plan=plan,
            status="ACTIVE",
            end_date=date.today() - timedelta(days=1),
        )

        # Membresía vigente
        client2 = ClientFactory(gym=gym)
        ClientMembershipFactory(
            client=client2,
            plan=plan,
            status="ACTIVE",
            end_date=date.today() + timedelta(days=10),
        )

        expired_count = bulk_service.expire_memberships()

        assert expired_count == 1

        from clients.models import ClientMembership
        m1 = ClientMembership.objects.get(client=client1)
        m2 = ClientMembership.objects.get(client=client2)

        assert m1.status == "EXPIRED"
        assert m2.status == "ACTIVE"
