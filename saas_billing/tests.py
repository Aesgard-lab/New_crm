"""
Tests for SaaS Billing system.

Tests cover:
- Alert service
- Task service (subscription management)
- Health monitoring
- Plan limits validation
"""
import pytest
from datetime import date, timedelta
from decimal import Decimal
from unittest.mock import patch, MagicMock

from django.core import mail
from django.core.cache import cache

from saas_billing.models import (
    SubscriptionPlan, GymSubscription, Invoice, 
    PaymentAttempt, BillingConfig
)
from saas_billing.alerts import SuperadminAlertService, AlertConfig
from saas_billing.tasks import SubscriptionTaskService
from saas_billing.health import HealthMonitorService, WebhookHealthStatus
from saas_billing.limits import PlanLimitsService, LimitStatus
from organizations.models import Gym
from accounts.models import User


@pytest.fixture
def billing_config(db):
    """Create billing configuration."""
    config, _ = BillingConfig.objects.get_or_create(
        pk=1,
        defaults={
            'company_name': 'Test SaaS Company',
            'company_tax_id': 'B12345678',
            'company_address': 'Test Address',
            'company_email': 'billing@test.com',
            'grace_period_days': 15,
            'enable_auto_suspension': True,
        }
    )
    return config


@pytest.fixture
def subscription_plan(db):
    """Create a test subscription plan."""
    return SubscriptionPlan.objects.create(
        name='Test Plan',
        price_monthly=Decimal('49.99'),
        price_yearly=Decimal('499.99'),
        max_members=100,
        max_staff=5,
        module_pos=True,
        module_calendar=True,
        is_active=True,
    )


@pytest.fixture
def unlimited_plan(db):
    """Create unlimited plan."""
    return SubscriptionPlan.objects.create(
        name='Unlimited Plan',
        price_monthly=Decimal('199.99'),
        max_members=None,  # Unlimited
        max_staff=None,
        is_active=True,
    )


@pytest.fixture
def gym_with_subscription(db, subscription_plan):
    """Create a gym with active subscription."""
    gym = Gym.objects.create(
        name='Test Gym',
        email='gym@test.com',
        slug='test-gym',
    )
    
    GymSubscription.objects.create(
        gym=gym,
        plan=subscription_plan,
        status='ACTIVE',
        billing_frequency='MONTHLY',
        current_period_start=date.today() - timedelta(days=15),
        current_period_end=date.today() + timedelta(days=15),
    )
    
    return gym


@pytest.fixture
def overdue_gym(db, subscription_plan):
    """Create a gym with overdue subscription."""
    gym = Gym.objects.create(
        name='Overdue Gym',
        email='overdue@test.com',
        slug='overdue-gym',
    )
    
    GymSubscription.objects.create(
        gym=gym,
        plan=subscription_plan,
        status='ACTIVE',
        billing_frequency='MONTHLY',
        current_period_start=date.today() - timedelta(days=45),
        current_period_end=date.today() - timedelta(days=5),  # 5 days overdue
    )
    
    return gym


@pytest.fixture
def superadmin_user(db):
    """Create a superadmin user."""
    return User.objects.create_user(
        email='superadmin@test.com',
        password='testpass123',
        first_name='Super',
        last_name='Admin',
        is_superuser=True,
        is_staff=True,
    )


# ==================== Alert Service Tests ====================

class TestAlertService:
    """Tests for SuperadminAlertService."""
    
    def test_get_superadmin_emails(self, superadmin_user):
        """Test getting superadmin emails."""
        service = SuperadminAlertService()
        emails = service.get_superadmin_emails()
        
        assert 'superadmin@test.com' in emails
    
    def test_send_alert_success(self, superadmin_user, settings):
        """Test sending alert email."""
        settings.EMAIL_BACKEND = 'django.core.mail.backends.locmem.EmailBackend'
        
        service = SuperadminAlertService()
        result = service.send_alert(
            subject='Test Alert',
            message='This is a test alert',
            level='warning'
        )
        
        assert result is True
        assert len(mail.outbox) == 1
        assert '⚠️' in mail.outbox[0].subject
        assert 'Test Alert' in mail.outbox[0].subject
    
    def test_send_alert_no_superadmins(self, db):
        """Test alert when no superadmins exist."""
        # Delete all superadmins
        User.objects.filter(is_superuser=True).delete()
        
        service = SuperadminAlertService()
        result = service.send_alert('Test', 'Test message')
        
        assert result is False
    
    def test_calculate_current_mrr(self, gym_with_subscription):
        """Test MRR calculation."""
        service = SuperadminAlertService()
        mrr = service.calculate_current_mrr()
        
        assert mrr == Decimal('49.99')


# ==================== Task Service Tests ====================

class TestTaskService:
    """Tests for SubscriptionTaskService."""
    
    def test_process_overdue_marks_past_due(self, overdue_gym, billing_config):
        """Test that overdue subscriptions are marked as PAST_DUE."""
        service = SubscriptionTaskService()
        
        with patch.object(service, '_billing_config', billing_config):
            stats = service.process_overdue_subscriptions()
        
        assert stats['marked_past_due'] >= 1
        
        overdue_gym.refresh_from_db()
        assert overdue_gym.subscription.status == 'PAST_DUE'
    
    def test_process_overdue_suspends_after_grace(self, db, subscription_plan, billing_config):
        """Test suspension after grace period."""
        # Create gym past grace period
        gym = Gym.objects.create(
            name='Past Grace Gym',
            email='pastgrace@test.com',
            slug='past-grace-gym',
        )
        
        GymSubscription.objects.create(
            gym=gym,
            plan=subscription_plan,
            status='PAST_DUE',
            billing_frequency='MONTHLY',
            current_period_start=date.today() - timedelta(days=60),
            current_period_end=date.today() - timedelta(days=30),
            suspension_date=date.today() - timedelta(days=20),  # Past 15-day grace
        )
        
        service = SubscriptionTaskService()
        service._billing_config = billing_config
        
        stats = service.process_overdue_subscriptions()
        
        assert stats['suspended'] >= 1
        
        gym.refresh_from_db()
        assert gym.subscription.status == 'SUSPENDED'
    
    def test_generate_pending_invoices(self, gym_with_subscription, billing_config):
        """Test invoice generation for due subscriptions."""
        # Make subscription due for renewal
        sub = gym_with_subscription.subscription
        sub.current_period_end = date.today()
        sub.auto_renew = True
        sub.save()
        
        service = SubscriptionTaskService()
        service._billing_config = billing_config
        
        initial_count = Invoice.objects.count()
        stats = service.generate_pending_invoices()
        
        assert stats['invoices_created'] >= 1
        assert Invoice.objects.count() > initial_count


# ==================== Health Monitor Tests ====================

class TestHealthMonitor:
    """Tests for HealthMonitorService."""
    
    def setup_method(self):
        """Clear cache before each test."""
        cache.clear()
    
    def test_record_webhook_event_success(self, db):
        """Test recording successful webhook."""
        service = HealthMonitorService()
        
        service.record_webhook_event('invoice.paid', True)
        
        health = service.get_webhook_health()
        assert health.successful_24h >= 1
        assert health.consecutive_failures == 0
    
    def test_record_webhook_event_failure(self, db):
        """Test recording failed webhook."""
        service = HealthMonitorService()
        
        service.record_webhook_event('invoice.paid', False, 'Test error')
        
        health = service.get_webhook_health()
        assert health.failed_24h >= 1
        assert health.consecutive_failures == 1
        assert health.last_error == 'Test error'
    
    def test_consecutive_failures_tracked(self, db, superadmin_user, settings):
        """Test consecutive failure counting."""
        settings.EMAIL_BACKEND = 'django.core.mail.backends.locmem.EmailBackend'
        service = HealthMonitorService()
        
        for i in range(5):
            service.record_webhook_event('test', False, f'Error {i}')
        
        health = service.get_webhook_health()
        assert health.consecutive_failures == 5
        assert not health.is_healthy
    
    def test_success_resets_consecutive_failures(self, db):
        """Test that success resets failure counter."""
        service = HealthMonitorService()
        
        service.record_webhook_event('test', False, 'Error')
        service.record_webhook_event('test', False, 'Error')
        service.record_webhook_event('test', True)  # Success
        
        health = service.get_webhook_health()
        assert health.consecutive_failures == 0
    
    def test_get_subscription_health(self, gym_with_subscription, overdue_gym):
        """Test subscription health metrics."""
        service = HealthMonitorService()
        
        health = service.get_subscription_health()
        
        assert health.total_active >= 1
    
    def test_overall_status_healthy(self, db):
        """Test healthy overall status."""
        service = HealthMonitorService()
        
        status = service._calculate_overall_status()
        assert status == 'healthy'
    
    def test_get_health_dashboard(self, db):
        """Test complete health dashboard."""
        service = HealthMonitorService()
        
        dashboard = service.get_health_dashboard()
        
        assert 'timestamp' in dashboard
        assert 'webhook' in dashboard
        assert 'payments' in dashboard
        assert 'subscriptions' in dashboard
        assert 'overall_status' in dashboard


# ==================== Plan Limits Tests ====================

class TestPlanLimits:
    """Tests for PlanLimitsService."""
    
    def test_check_limit_unlimited(self):
        """Test checking unlimited limit."""
        service = PlanLimitsService()
        
        status = service.check_limit(
            current=500,
            limit=None,
            limit_name='members'
        )
        
        assert status.is_unlimited
        assert not status.is_exceeded
        assert not status.is_near_limit
    
    def test_check_limit_within(self):
        """Test checking limit within bounds."""
        service = PlanLimitsService()
        
        status = service.check_limit(
            current=50,
            limit=100,
            limit_name='members'
        )
        
        assert not status.is_exceeded
        assert not status.is_near_limit
        assert status.percentage_used == Decimal('50.0')
    
    def test_check_limit_near(self):
        """Test checking limit near threshold."""
        service = PlanLimitsService()
        
        status = service.check_limit(
            current=85,
            limit=100,
            limit_name='members'
        )
        
        assert not status.is_exceeded
        assert status.is_near_limit
        assert status.percentage_used == Decimal('85.0')
    
    def test_check_limit_exceeded(self):
        """Test checking exceeded limit."""
        service = PlanLimitsService()
        
        status = service.check_limit(
            current=110,
            limit=100,
            limit_name='members'
        )
        
        assert status.is_exceeded
        assert not status.is_near_limit
        assert status.percentage_used == Decimal('110.0')
    
    def test_get_gym_limits(self, gym_with_subscription):
        """Test getting gym limits report."""
        service = PlanLimitsService()
        
        report = service.get_gym_limits(gym_with_subscription)
        
        assert report is not None
        assert report.gym_name == 'Test Gym'
        assert report.plan_name == 'Test Plan'
        assert report.members.max_value == 100
        assert report.staff.max_value == 5
    
    def test_get_gym_limits_no_subscription(self, db):
        """Test gym without subscription returns None."""
        gym = Gym.objects.create(
            name='No Sub Gym',
            slug='no-sub-gym',
        )
        
        service = PlanLimitsService()
        report = service.get_gym_limits(gym)
        
        assert report is None
    
    def test_validate_can_add_member_success(self, gym_with_subscription):
        """Test validation allows adding member."""
        service = PlanLimitsService()
        
        can_add, message = service.validate_can_add_member(gym_with_subscription)
        
        assert can_add
        assert message == 'OK'
    
    def test_validate_can_add_member_at_limit(self, db, subscription_plan):
        """Test validation blocks at limit."""
        # Create plan with limit of 1
        plan = SubscriptionPlan.objects.create(
            name='Tiny Plan',
            price_monthly=Decimal('9.99'),
            max_members=1,
            is_active=True,
        )
        
        gym = Gym.objects.create(
            name='Tiny Gym',
            slug='tiny-gym',
        )
        
        GymSubscription.objects.create(
            gym=gym,
            plan=plan,
            status='ACTIVE',
            billing_frequency='MONTHLY',
            current_period_start=date.today(),
            current_period_end=date.today() + timedelta(days=30),
        )
        
        # Add one member
        from clients.models import Client
        Client.objects.create(
            gym=gym,
            first_name='Test',
            last_name='Member',
            email='member@test.com',
            status='ACTIVE',
        )
        
        service = PlanLimitsService()
        can_add, message = service.validate_can_add_member(gym)
        
        assert not can_add
        assert 'Límite' in message or 'límite' in message


# ==================== Invoice Model Tests ====================

class TestInvoiceModel:
    """Tests for Invoice model."""
    
    def test_generate_invoice_number(self, gym_with_subscription):
        """Test invoice number generation."""
        invoice = Invoice(
            gym=gym_with_subscription,
            amount=Decimal('49.99'),
            tax_amount=Decimal('10.50'),
            total_amount=Decimal('60.49'),
            issue_date=date.today(),
            due_date=date.today() + timedelta(days=7),
        )
        
        number = invoice.generate_invoice_number()
        
        assert number.startswith('INV-')
        assert str(date.today().year) in number
    
    def test_invoice_number_unique(self, gym_with_subscription):
        """Test invoice numbers are sequential."""
        invoice1 = Invoice.objects.create(
            gym=gym_with_subscription,
            invoice_number=Invoice().generate_invoice_number(),
            amount=Decimal('49.99'),
            tax_amount=Decimal('10.50'),
            total_amount=Decimal('60.49'),
            issue_date=date.today(),
            due_date=date.today() + timedelta(days=7),
        )
        
        invoice2 = Invoice(
            gym=gym_with_subscription,
            amount=Decimal('49.99'),
            tax_amount=Decimal('10.50'),
            total_amount=Decimal('60.49'),
            issue_date=date.today(),
            due_date=date.today() + timedelta(days=7),
        )
        
        number2 = invoice2.generate_invoice_number()
        
        # Second number should be higher
        num1 = int(invoice1.invoice_number.split('-')[-1])
        num2 = int(number2.split('-')[-1])
        assert num2 > num1


# ==================== Subscription Plan Tests ====================

class TestSubscriptionPlan:
    """Tests for SubscriptionPlan model."""
    
    def test_calculate_transaction_fee_none(self, subscription_plan):
        """Test no transaction fee."""
        subscription_plan.transaction_fee_type = 'NONE'
        
        fee = subscription_plan.calculate_transaction_fee(Decimal('100.00'))
        
        assert fee == Decimal('0.00')
    
    def test_calculate_transaction_fee_percent(self, subscription_plan):
        """Test percentage transaction fee."""
        subscription_plan.transaction_fee_type = 'PERCENT'
        subscription_plan.transaction_fee_percent = Decimal('2.50')
        
        fee = subscription_plan.calculate_transaction_fee(Decimal('100.00'))
        
        assert fee == Decimal('2.50')
    
    def test_calculate_transaction_fee_fixed(self, subscription_plan):
        """Test fixed transaction fee."""
        subscription_plan.transaction_fee_type = 'FIXED'
        subscription_plan.transaction_fee_fixed = Decimal('0.30')
        
        fee = subscription_plan.calculate_transaction_fee(Decimal('100.00'))
        
        assert fee == Decimal('0.30')
    
    def test_calculate_transaction_fee_hybrid(self, subscription_plan):
        """Test hybrid transaction fee."""
        subscription_plan.transaction_fee_type = 'HYBRID'
        subscription_plan.transaction_fee_percent = Decimal('2.00')
        subscription_plan.transaction_fee_fixed = Decimal('0.25')
        
        fee = subscription_plan.calculate_transaction_fee(Decimal('100.00'))
        
        assert fee == Decimal('2.25')  # 2% + 0.25
    
    def test_cash_excluded(self, subscription_plan):
        """Test cash payments excluded from fees."""
        subscription_plan.transaction_fee_type = 'PERCENT'
        subscription_plan.transaction_fee_percent = Decimal('2.50')
        subscription_plan.transaction_fee_exclude_cash = True
        
        fee = subscription_plan.calculate_transaction_fee(
            Decimal('100.00'),
            is_cash=True
        )
        
        assert fee == Decimal('0.00')
    
    def test_get_enabled_modules(self, subscription_plan):
        """Test getting enabled modules."""
        modules = subscription_plan.get_enabled_modules()
        
        assert 'POS' in modules
        assert 'Calendario' in modules
