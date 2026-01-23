"""
Tests for Billing Improvements:
- Charge tracking fields on ClientMembership
- Bulk charge API endpoint
- Auto-charge configuration in FinanceSettings
"""
from django.test import TestCase, Client as TestClient
from django.contrib.auth import get_user_model
from django.urls import reverse
from django.utils import timezone
from datetime import time, timedelta
from decimal import Decimal
import json
from unittest.mock import patch, MagicMock

from organizations.models import Gym
from accounts.models_memberships import GymMembership
from clients.models import Client, ClientMembership
from memberships.models import MembershipPlan
from finance.models import FinanceSettings, PaymentMethod

User = get_user_model()


class ChargeTrackingFieldsTest(TestCase):
    """Test charge tracking fields on ClientMembership model"""
    
    def setUp(self):
        self.gym = Gym.objects.create(name="Test Gym")
        self.client_obj = Client.objects.create(
            gym=self.gym, 
            first_name="John", 
            last_name="Doe", 
            email="john@test.com"
        )
        self.plan = MembershipPlan.objects.create(
            gym=self.gym,
            name="Monthly",
            base_price=Decimal("30.00"),
            is_active=True
        )
        self.client_membership = ClientMembership.objects.create(
            client=self.client_obj,
            gym=self.gym,
            plan=self.plan,
            name="Monthly Membership",
            start_date=timezone.now().date(),
            end_date=timezone.now().date() + timedelta(days=30),
            price=Decimal("30.00"),
            status='ACTIVE'
        )
    
    def test_charge_tracking_fields_exist(self):
        """Test that charge tracking fields exist and have correct defaults"""
        cm = self.client_membership
        
        # Check fields exist
        self.assertTrue(hasattr(cm, 'failed_charge_attempts'))
        self.assertTrue(hasattr(cm, 'last_charge_attempt'))
        self.assertTrue(hasattr(cm, 'last_charge_error'))
        
        # Check default values
        self.assertEqual(cm.failed_charge_attempts, 0)
        self.assertIsNone(cm.last_charge_attempt)
        self.assertEqual(cm.last_charge_error, '')
    
    def test_increment_failed_attempts(self):
        """Test incrementing failed charge attempts"""
        cm = self.client_membership
        
        cm.failed_charge_attempts += 1
        cm.last_charge_attempt = timezone.now()
        cm.last_charge_error = "Card declined"
        cm.save()
        
        cm.refresh_from_db()
        self.assertEqual(cm.failed_charge_attempts, 1)
        self.assertIsNotNone(cm.last_charge_attempt)
        self.assertEqual(cm.last_charge_error, "Card declined")
    
    def test_reset_failed_attempts_on_success(self):
        """Test that failed attempts reset to 0 after successful charge"""
        cm = self.client_membership
        
        # Simulate previous failures
        cm.failed_charge_attempts = 3
        cm.last_charge_error = "Insufficient funds"
        cm.save()
        
        # Simulate successful charge
        cm.failed_charge_attempts = 0
        cm.last_charge_error = ''
        cm.save()
        
        cm.refresh_from_db()
        self.assertEqual(cm.failed_charge_attempts, 0)
        self.assertEqual(cm.last_charge_error, '')


class AutoChargeSettingsTest(TestCase):
    """Test auto-charge configuration fields in FinanceSettings"""
    
    def setUp(self):
        self.gym = Gym.objects.create(name="Test Gym")
    
    def test_auto_charge_fields_exist(self):
        """Test that auto-charge configuration fields exist"""
        settings = FinanceSettings.objects.create(gym=self.gym)
        
        self.assertTrue(hasattr(settings, 'auto_charge_enabled'))
        self.assertTrue(hasattr(settings, 'auto_charge_time'))
        self.assertTrue(hasattr(settings, 'auto_charge_max_retries'))
        self.assertTrue(hasattr(settings, 'auto_charge_retry_days'))
    
    def test_auto_charge_default_values(self):
        """Test default values for auto-charge settings"""
        settings = FinanceSettings.objects.create(gym=self.gym)
        
        self.assertFalse(settings.auto_charge_enabled)
        # auto_charge_time is stored as string '08:00' by default
        self.assertEqual(str(settings.auto_charge_time)[:5], '08:00')
        self.assertEqual(settings.auto_charge_max_retries, 3)
        self.assertEqual(settings.auto_charge_retry_days, 3)
    
    def test_auto_charge_custom_values(self):
        """Test setting custom values for auto-charge"""
        settings = FinanceSettings.objects.create(
            gym=self.gym,
            auto_charge_enabled=True,
            auto_charge_time=time(10, 30),
            auto_charge_max_retries=5,
            auto_charge_retry_days=7
        )
        
        self.assertTrue(settings.auto_charge_enabled)
        self.assertEqual(settings.auto_charge_time, time(10, 30))
        self.assertEqual(settings.auto_charge_max_retries, 5)
        self.assertEqual(settings.auto_charge_retry_days, 7)
    
    def test_auto_charge_settings_update(self):
        """Test updating auto-charge settings"""
        settings = FinanceSettings.objects.create(gym=self.gym)
        
        settings.auto_charge_enabled = True
        settings.auto_charge_max_retries = 10
        settings.save()
        
        settings.refresh_from_db()
        self.assertTrue(settings.auto_charge_enabled)
        self.assertEqual(settings.auto_charge_max_retries, 10)


class BulkChargeAPITest(TestCase):
    """Test bulk charge API endpoint - URL configuration only"""
    
    def test_bulk_charge_url_exists(self):
        """Test that bulk charge URL is properly configured"""
        url = reverse('api_bulk_subscription_charge')
        self.assertIsNotNone(url)
        self.assertEqual(url, '/sales/api/subscription/bulk-charge/')
    
    def test_bulk_charge_url_resolves(self):
        """Test that the URL resolves to the correct view"""
        from django.urls import resolve
        from sales import api
        url = reverse('api_bulk_subscription_charge')
        resolved = resolve(url)
        self.assertEqual(resolved.func, api.bulk_subscription_charge)


class ChargeTrackingIntegrationTest(TestCase):
    """Integration tests for charge tracking workflow"""
    
    def setUp(self):
        self.gym = Gym.objects.create(name="Test Gym")
        self.user = User.objects.create_user(email="admin@gym.com", password="testpass123")
        GymMembership.objects.create(user=self.user, gym=self.gym, role=GymMembership.Role.ADMIN)
        
        self.plan = MembershipPlan.objects.create(
            gym=self.gym,
            name="Basic",
            base_price=Decimal("25.00"),
            is_active=True
        )
        
        self.client_obj = Client.objects.create(
            gym=self.gym,
            first_name="Test",
            last_name="User",
            email="test@user.com",
            stripe_customer_id="cus_test123"
        )
        
        self.client_membership = ClientMembership.objects.create(
            client=self.client_obj,
            gym=self.gym,
            plan=self.plan,
            name="Basic",
            start_date=timezone.now().date(),
            end_date=timezone.now().date() + timedelta(days=30),
            price=Decimal("25.00"),
            status='ACTIVE'
        )
        
        FinanceSettings.objects.create(
            gym=self.gym,
            auto_charge_enabled=True,
            auto_charge_max_retries=3,
            auto_charge_retry_days=2
        )
    
    def test_should_retry_charge_within_limit(self):
        """Test logic for determining if retry should happen"""
        cm = self.client_membership
        settings = FinanceSettings.objects.get(gym=self.gym)
        
        # First attempt - should retry
        cm.failed_charge_attempts = 1
        cm.save()
        
        should_retry = cm.failed_charge_attempts < settings.auto_charge_max_retries
        self.assertTrue(should_retry)
    
    def test_should_not_retry_after_max_attempts(self):
        """Test that retry stops after max attempts"""
        cm = self.client_membership
        settings = FinanceSettings.objects.get(gym=self.gym)
        
        # Max attempts reached
        cm.failed_charge_attempts = 3
        cm.save()
        
        should_retry = cm.failed_charge_attempts < settings.auto_charge_max_retries
        self.assertFalse(should_retry)
    
    def test_retry_timing_check(self):
        """Test that retry respects days between attempts"""
        cm = self.client_membership
        settings = FinanceSettings.objects.get(gym=self.gym)
        
        # Last attempt was yesterday
        cm.failed_charge_attempts = 1
        cm.last_charge_attempt = timezone.now() - timedelta(days=1)
        cm.save()
        
        days_since_last = (timezone.now() - cm.last_charge_attempt).days
        should_retry_now = days_since_last >= settings.auto_charge_retry_days
        
        # With retry_days=2, 1 day is not enough
        self.assertFalse(should_retry_now)
        
        # Set last attempt to 3 days ago
        cm.last_charge_attempt = timezone.now() - timedelta(days=3)
        cm.save()
        
        days_since_last = (timezone.now() - cm.last_charge_attempt).days
        should_retry_now = days_since_last >= settings.auto_charge_retry_days
        
        # Now it should be ok to retry
        self.assertTrue(should_retry_now)
