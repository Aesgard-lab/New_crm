"""
Tests for membership workflows.

Covers:
- Membership creation and status management
- Session tracking for limited plans
- Eligibility criteria validation
- Pause functionality
"""
import pytest
from datetime import timedelta
from decimal import Decimal
from django.utils import timezone

from tests.factories import (
    GymFactory,
    ClientFactory,
    MembershipPlanFactory,
    ClientMembershipFactory,
    PackPlanFactory,
    ExpiredMembershipFactory,
)


@pytest.mark.django_db
class TestMembershipPlanEligibility:
    """Test plan eligibility criteria for clients."""

    def test_plan_no_restriction_is_always_eligible(self):
        """Any client can access plans without restrictions."""
        gym = GymFactory()
        plan = MembershipPlanFactory(gym=gym, eligibility_criteria='NONE')
        client = ClientFactory(gym=gym)
        
        is_eligible, _ = plan.is_client_eligible(client)
        assert is_eligible is True

    def test_plan_never_had_membership_new_client(self):
        """New client without history is eligible for 'never had' plans."""
        gym = GymFactory()
        plan = MembershipPlanFactory(
            gym=gym,
            eligibility_criteria='NEVER_HAD_MEMBERSHIP'
        )
        client = ClientFactory(gym=gym)
        
        is_eligible, _ = plan.is_client_eligible(client)
        assert is_eligible is True

    def test_plan_never_had_membership_existing_client(self):
        """Client with history is NOT eligible for 'never had' plans."""
        gym = GymFactory()
        plan = MembershipPlanFactory(
            gym=gym,
            eligibility_criteria='NEVER_HAD_MEMBERSHIP'
        )
        client = ClientFactory(gym=gym)
        
        # Give client a membership
        ClientMembershipFactory(client=client, gym=gym)
        
        is_eligible, reason = plan.is_client_eligible(client)
        assert is_eligible is False
        assert reason != ""

    def test_plan_visibility_hide_for_ineligible(self):
        """Ineligible client should not see plan when set to HIDE."""
        gym = GymFactory()
        plan = MembershipPlanFactory(
            gym=gym,
            eligibility_criteria='NEVER_HAD_MEMBERSHIP',
            visibility_for_ineligible='HIDE'
        )
        client = ClientFactory(gym=gym)
        
        # Make client ineligible
        ClientMembershipFactory(client=client, gym=gym)
        
        should_show, is_eligible, _ = plan.should_show_to_client(client)
        assert should_show is False
        assert is_eligible is False

    def test_plan_visibility_show_locked_for_ineligible(self):
        """Ineligible client should see locked plan when set to SHOW_LOCKED."""
        gym = GymFactory()
        plan = MembershipPlanFactory(
            gym=gym,
            eligibility_criteria='NEVER_HAD_MEMBERSHIP',
            visibility_for_ineligible='SHOW_LOCKED'
        )
        client = ClientFactory(gym=gym)
        
        # Make client ineligible
        ClientMembershipFactory(client=client, gym=gym)
        
        should_show, is_eligible, _ = plan.should_show_to_client(client)
        assert should_show is True
        assert is_eligible is False


@pytest.mark.django_db
class TestClientMembership:
    """Test ClientMembership model functionality."""

    def test_membership_created_with_correct_dates(self):
        """Membership should have correct start/end dates."""
        membership = ClientMembershipFactory()
        
        assert membership.start_date == timezone.now().date()
        assert membership.end_date == timezone.now().date() + timedelta(days=30)
        assert membership.status == "ACTIVE"

    def test_unlimited_membership_sessions(self):
        """Unlimited membership should report None for remaining."""
        membership = ClientMembershipFactory(
            sessions_total=0,
            sessions_used=5
        )
        
        assert membership.is_unlimited is True
        assert membership.sessions_remaining is None
        assert membership.usage_percentage is None

    def test_limited_membership_sessions_tracking(self):
        """Limited membership should track session usage correctly."""
        membership = ClientMembershipFactory(
            sessions_total=10,
            sessions_used=3
        )
        
        assert membership.is_unlimited is False
        assert membership.sessions_remaining == 7
        assert membership.usage_percentage == 30

    def test_limited_membership_sessions_exhausted(self):
        """Sessions remaining should not go negative."""
        membership = ClientMembershipFactory(
            sessions_total=5,
            sessions_used=7  # Used more than total
        )
        
        assert membership.sessions_remaining == 0
        assert membership.usage_percentage == 100

    def test_expired_membership_status(self):
        """Expired membership should have correct dates and status."""
        membership = ExpiredMembershipFactory()
        
        assert membership.end_date < timezone.now().date()
        assert membership.status == "EXPIRED"


@pytest.mark.django_db
class TestPackMembership:
    """Test pack/session-based memberships."""

    def test_pack_plan_creation(self):
        """Pack plan should be non-recurring with validity days."""
        plan = PackPlanFactory(pack_validity_days=60)
        
        assert plan.is_recurring is False
        assert plan.pack_validity_days == 60

    def test_pack_membership_session_decrement(self):
        """Sessions should be decremented correctly."""
        membership = ClientMembershipFactory(
            sessions_total=10,
            sessions_used=0
        )
        
        # Simulate using a session
        membership.sessions_used += 1
        membership.save()
        
        assert membership.sessions_remaining == 9
        assert membership.usage_percentage == 10


@pytest.mark.django_db
class TestMembershipPricing:
    """Test membership pricing calculations."""

    def test_membership_copies_plan_price(self):
        """Membership should copy price from plan."""
        gym = GymFactory()
        plan = MembershipPlanFactory(gym=gym, base_price=Decimal("79.99"))
        client = ClientFactory(gym=gym)
        
        membership = ClientMembershipFactory(
            client=client,
            gym=gym,
            plan=plan
        )
        
        assert membership.price == Decimal("79.99")

    def test_membership_recurring_status(self):
        """Membership should inherit recurring status from plan."""
        gym = GymFactory()
        plan = MembershipPlanFactory(gym=gym, is_recurring=True)
        
        membership = ClientMembershipFactory(plan=plan)
        assert membership.is_recurring is True
        
        pack_plan = PackPlanFactory(gym=gym)
        pack_membership = ClientMembershipFactory(plan=pack_plan)
        assert pack_membership.is_recurring is False


@pytest.mark.django_db
class TestMembershipStatuses:
    """Test different membership statuses."""

    def test_active_membership(self):
        """Active membership should have ACTIVE status."""
        membership = ClientMembershipFactory(status="ACTIVE")
        assert membership.status == "ACTIVE"

    def test_paused_membership(self):
        """Paused membership should have PAUSED status."""
        membership = ClientMembershipFactory(status="PAUSED")
        assert membership.status == "PAUSED"

    def test_pending_payment_membership(self):
        """Pending payment membership status."""
        membership = ClientMembershipFactory(status="PENDING_PAYMENT")
        assert membership.status == "PENDING_PAYMENT"

    def test_cancelled_membership(self):
        """Cancelled membership status."""
        membership = ClientMembershipFactory(status="CANCELLED")
        assert membership.status == "CANCELLED"
