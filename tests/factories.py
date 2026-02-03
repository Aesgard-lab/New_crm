"""
Factory classes for creating test data with factory_boy.

Usage:
    from tests.factories import GymFactory, ClientFactory, MembershipPlanFactory

    # Create a gym with default values
    gym = GymFactory()

    # Create a client with specific gym
    client = ClientFactory(gym=gym, first_name="John")

    # Create with nested relations
    membership = ClientMembershipFactory(client__gym=gym)
"""
import factory
from factory import fuzzy
from factory.django import DjangoModelFactory
from django.contrib.auth import get_user_model
from django.utils import timezone
from datetime import timedelta
from decimal import Decimal

User = get_user_model()


# ============================================================================
# Auth Factories
# ============================================================================

class UserFactory(DjangoModelFactory):
    """Factory for creating test users."""
    
    class Meta:
        model = User
        skip_postgeneration_save = True

    email = factory.Sequence(lambda n: f"user_{n}@test.com")
    first_name = factory.Faker("first_name", locale="es_ES")
    last_name = factory.Faker("last_name", locale="es_ES")
    is_active = True
    is_staff = False

    @factory.post_generation
    def password(self, create, extracted, **kwargs):
        password = extracted or "TestPassword123!"
        self.set_password(password)
        if create:
            self.save()


class StaffUserFactory(UserFactory):
    """Factory for staff users."""
    is_staff = True


class SuperuserFactory(UserFactory):
    """Factory for superusers."""
    is_staff = True
    
    @classmethod
    def _create(cls, model_class, *args, **kwargs):
        manager = model_class._default_manager
        return manager.create_superuser(*args, **kwargs)


# ============================================================================
# Organization Factories
# ============================================================================

class FranchiseFactory(DjangoModelFactory):
    """Factory for creating franchises."""
    
    class Meta:
        model = "organizations.Franchise"
    
    name = factory.Sequence(lambda n: f"Franchise {n}")


class GymFactory(DjangoModelFactory):
    """Factory for creating gyms."""
    
    class Meta:
        model = "organizations.Gym"
    
    name = factory.Sequence(lambda n: f"Test Gym {n}")
    slug = factory.LazyAttribute(lambda obj: f"test-gym-{obj.name.lower().replace(' ', '-')}")
    commercial_name = factory.LazyAttribute(lambda obj: obj.name)
    email = factory.LazyAttribute(lambda obj: f"contact@{obj.slug}.com")
    phone = factory.Faker("phone_number", locale="es_ES")
    address = factory.Faker("address", locale="es_ES")
    city = factory.Faker("city", locale="es_ES")
    zip_code = factory.Faker("postcode", locale="es_ES")
    country = "España"
    language = "es"


# ============================================================================
# Finance Factories
# ============================================================================

class TaxRateFactory(DjangoModelFactory):
    """Factory for tax rates."""
    
    class Meta:
        model = "finance.TaxRate"
    
    gym = factory.SubFactory(GymFactory)
    name = "IVA 21%"
    rate_percent = Decimal("21.00")
    is_active = True


class PaymentMethodFactory(DjangoModelFactory):
    """Factory for payment methods."""
    
    class Meta:
        model = "finance.PaymentMethod"
    
    gym = factory.SubFactory(GymFactory)
    name = "Efectivo"
    is_cash = True
    is_active = True
    gateway = "NONE"


class StripePaymentMethodFactory(PaymentMethodFactory):
    """Factory for Stripe payment method."""
    name = "Tarjeta Online"
    is_cash = False
    available_for_online = True
    gateway = "STRIPE"


# ============================================================================
# Client Factories
# ============================================================================

class ClientFactory(DjangoModelFactory):
    """Factory for creating clients."""
    
    class Meta:
        model = "clients.Client"
    
    gym = factory.SubFactory(GymFactory)
    first_name = factory.Faker("first_name", locale="es_ES")
    last_name = factory.Faker("last_name", locale="es_ES")
    email = factory.LazyAttribute(lambda obj: f"{obj.first_name.lower()}.{obj.last_name.lower()}@test.com")
    phone_number = factory.Faker("phone_number", locale="es_ES")
    status = "ACTIVE"
    document_type = "DNI"
    dni = factory.Sequence(lambda n: f"{12345678 + n}A")
    
    # Optional user link
    user = None


class ClientWithUserFactory(ClientFactory):
    """Client linked to a user account."""
    user = factory.SubFactory(UserFactory)
    email = factory.LazyAttribute(lambda obj: obj.user.email if obj.user else f"client@test.com")


class LeadClientFactory(ClientFactory):
    """Factory for lead/prospect clients."""
    status = "LEAD"
    email = ""  # Leads may not have email


# ============================================================================
# Membership Factories
# ============================================================================

class MembershipPlanFactory(DjangoModelFactory):
    """Factory for membership plans."""
    
    class Meta:
        model = "memberships.MembershipPlan"
    
    gym = factory.SubFactory(GymFactory)
    name = factory.Sequence(lambda n: f"Plan Básico {n}")
    description = "Plan de prueba para tests"
    base_price = Decimal("49.99")
    is_recurring = True
    frequency_amount = 1
    frequency_unit = "MONTH"
    is_active = True
    is_visible_online = True


class PackPlanFactory(MembershipPlanFactory):
    """Factory for pack/session-based plans."""
    name = factory.Sequence(lambda n: f"Bono {n} Sesiones")
    is_recurring = False
    pack_validity_days = 30


class ClientMembershipFactory(DjangoModelFactory):
    """Factory for client memberships."""
    
    class Meta:
        model = "clients.ClientMembership"
    
    client = factory.SubFactory(ClientFactory)
    gym = factory.SelfAttribute("client.gym")
    plan = factory.SubFactory(
        MembershipPlanFactory,
        gym=factory.SelfAttribute("..client.gym")
    )
    name = factory.LazyAttribute(lambda obj: obj.plan.name if obj.plan else "Membresía Test")
    start_date = factory.LazyFunction(lambda: timezone.now().date())
    end_date = factory.LazyAttribute(
        lambda obj: obj.start_date + timedelta(days=30)
    )
    status = "ACTIVE"
    price = factory.LazyAttribute(lambda obj: obj.plan.base_price if obj.plan else Decimal("49.99"))
    is_recurring = factory.LazyAttribute(lambda obj: obj.plan.is_recurring if obj.plan else True)
    sessions_total = 0
    sessions_used = 0


class ExpiredMembershipFactory(ClientMembershipFactory):
    """Factory for expired memberships."""
    start_date = factory.LazyFunction(lambda: timezone.now().date() - timedelta(days=60))
    end_date = factory.LazyFunction(lambda: timezone.now().date() - timedelta(days=1))
    status = "EXPIRED"


# ============================================================================
# Activity Factories
# ============================================================================

class ActivityCategoryFactory(DjangoModelFactory):
    """Factory for activity categories."""
    
    class Meta:
        model = "activities.ActivityCategory"
    
    gym = factory.SubFactory(GymFactory)
    name = factory.Sequence(lambda n: f"Categoría {n}")


class ActivityFactory(DjangoModelFactory):
    """Factory for activities."""
    
    class Meta:
        model = "activities.Activity"
    
    gym = factory.SubFactory(GymFactory)
    name = factory.Sequence(lambda n: f"Actividad Test {n}")
    category = factory.SubFactory(
        ActivityCategoryFactory,
        gym=factory.SelfAttribute("..gym")
    )
    duration = 60
    base_capacity = 20


class ActivitySessionFactory(DjangoModelFactory):
    """Factory for activity sessions/classes."""
    
    class Meta:
        model = "activities.ActivitySession"
    
    gym = factory.SelfAttribute("activity.gym")
    activity = factory.SubFactory(ActivityFactory)
    start_datetime = factory.LazyFunction(
        lambda: timezone.now() + timedelta(days=1)
    )
    end_datetime = factory.LazyAttribute(
        lambda obj: obj.start_datetime + timedelta(hours=1)
    )
    status = "SCHEDULED"
    max_capacity = 20


# ============================================================================
# Booking Factories
# ============================================================================

class BookingFactory(DjangoModelFactory):
    """Factory for activity bookings."""
    
    class Meta:
        model = "activities.ActivitySessionBooking"
    
    client = factory.SubFactory(ClientFactory)
    session = factory.SubFactory(
        ActivitySessionFactory,
        activity__gym=factory.SelfAttribute("...client.gym")
    )
    status = "CONFIRMED"
    attendance_status = "PENDING"
    booked_at = factory.LazyFunction(timezone.now)


# ============================================================================
# Payment Factories
# ============================================================================

class ClientPaymentFactory(DjangoModelFactory):
    """Factory for client payment records."""
    
    class Meta:
        model = "finance.ClientPayment"
    
    client = factory.SubFactory(ClientFactory)
    amount = Decimal("49.99")
    currency = "EUR"
    status = "PAID"
    concept = "Cuota mensual"
    payment_method = "Visa **** 4242"


class StripePaymentFactory(ClientPaymentFactory):
    """Factory for Stripe payments."""
    stripe_payment_intent_id = factory.Sequence(lambda n: f"pi_test_{n}")


# ============================================================================
# Staff/Organization Factories
# ============================================================================

class GymMembershipFactory(DjangoModelFactory):
    """Factory for gym staff memberships."""
    
    class Meta:
        model = "accounts.GymMembership"
    
    user = factory.SubFactory(UserFactory)
    gym = factory.SubFactory(GymFactory)
    role = "ADMIN"
    is_active = True


class StaffMembershipFactory(GymMembershipFactory):
    """Factory for staff role membership."""
    role = "STAFF"
