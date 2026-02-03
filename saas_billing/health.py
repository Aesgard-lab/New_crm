"""
SaaS Health Monitoring Service.

Tracks webhook health, payment success rates, and system status.
Provides data for the superadmin health dashboard.
"""
from dataclasses import dataclass
from datetime import date, datetime, timedelta
from decimal import Decimal
from typing import Optional
import logging

from django.core.cache import cache
from django.db.models import Sum, Count, Q, Avg
from django.utils import timezone

from .models import (
    GymSubscription, FranchiseSubscription, Invoice,
    PaymentAttempt, BillingConfig
)

logger = logging.getLogger(__name__)


@dataclass
class WebhookHealthStatus:
    """Webhook health metrics."""
    total_received_24h: int = 0
    successful_24h: int = 0
    failed_24h: int = 0
    last_received: Optional[datetime] = None
    last_error: Optional[str] = None
    consecutive_failures: int = 0
    is_healthy: bool = True


@dataclass
class PaymentHealthStatus:
    """Payment processing health metrics."""
    success_rate_7d: Decimal = Decimal('100.0')
    total_attempts_7d: int = 0
    failed_attempts_7d: int = 0
    avg_retry_count: Decimal = Decimal('0.0')
    pending_retries: int = 0


@dataclass
class SubscriptionHealthStatus:
    """Subscription health metrics."""
    total_active: int = 0
    total_past_due: int = 0
    total_suspended: int = 0
    total_cancelled: int = 0
    at_risk_count: int = 0  # Past due + about to expire
    churn_rate_30d: Decimal = Decimal('0.0')


class HealthMonitorService:
    """
    Service for monitoring SaaS billing system health.
    """
    
    CACHE_PREFIX = 'saas_health_'
    CACHE_TTL = 300  # 5 minutes
    
    # ==================== Webhook Health ====================
    
    def record_webhook_event(self, event_type: str, success: bool, error: Optional[str] = None):
        """
        Record a webhook event for health tracking.
        Called from webhook handler.
        """
        key = f"{self.CACHE_PREFIX}webhooks"
        data = cache.get(key) or {
            'events': [],
            'consecutive_failures': 0,
            'last_error': None
        }
        
        # Add event
        event = {
            'type': event_type,
            'success': success,
            'timestamp': timezone.now().isoformat(),
            'error': error
        }
        data['events'].append(event)
        
        # Keep only last 24 hours of events
        cutoff = (timezone.now() - timedelta(hours=24)).isoformat()
        data['events'] = [e for e in data['events'] if e['timestamp'] > cutoff]
        
        # Track consecutive failures
        if success:
            data['consecutive_failures'] = 0
            data['last_error'] = None
        else:
            data['consecutive_failures'] += 1
            data['last_error'] = error
        
        cache.set(key, data, timeout=86400)  # 24 hours
        
        # Alert on consecutive failures
        if data['consecutive_failures'] >= 5:
            from .alerts import alert_service
            alert_service.alert_webhook_failures(
                data['consecutive_failures'],
                data['last_error'] or 'Unknown error'
            )
    
    def get_webhook_health(self) -> WebhookHealthStatus:
        """Get webhook health status."""
        key = f"{self.CACHE_PREFIX}webhooks"
        data = cache.get(key) or {'events': [], 'consecutive_failures': 0}
        
        events = data['events']
        successful = [e for e in events if e['success']]
        failed = [e for e in events if not e['success']]
        
        last_received = None
        if events:
            last_received = datetime.fromisoformat(events[-1]['timestamp'])
        
        return WebhookHealthStatus(
            total_received_24h=len(events),
            successful_24h=len(successful),
            failed_24h=len(failed),
            last_received=last_received,
            last_error=data.get('last_error'),
            consecutive_failures=data['consecutive_failures'],
            is_healthy=data['consecutive_failures'] < 3
        )
    
    # ==================== Payment Health ====================
    
    def get_payment_health(self) -> PaymentHealthStatus:
        """Get payment processing health status."""
        seven_days_ago = timezone.now() - timedelta(days=7)
        
        attempts = PaymentAttempt.objects.filter(
            attempted_at__gte=seven_days_ago
        )
        
        total = attempts.count()
        failed = attempts.filter(status='FAILED').count()
        pending_retries = attempts.filter(
            status='RETRYING',
            next_retry__isnull=False
        ).count()
        
        success_rate = Decimal('100.0')
        if total > 0:
            success_rate = Decimal((total - failed) / total * 100).quantize(Decimal('0.1'))
        
        # Average retries per invoice
        avg_retries = attempts.values('invoice').annotate(
            count=Count('id')
        ).aggregate(avg=Avg('count'))['avg'] or 0
        
        return PaymentHealthStatus(
            success_rate_7d=success_rate,
            total_attempts_7d=total,
            failed_attempts_7d=failed,
            avg_retry_count=Decimal(str(avg_retries)).quantize(Decimal('0.1')),
            pending_retries=pending_retries
        )
    
    # ==================== Subscription Health ====================
    
    def get_subscription_health(self) -> SubscriptionHealthStatus:
        """Get subscription health status."""
        today = date.today()
        thirty_days_ago = today - timedelta(days=30)
        seven_days_future = today + timedelta(days=7)
        
        # Status counts
        active = GymSubscription.objects.filter(status='ACTIVE').count()
        past_due = GymSubscription.objects.filter(status='PAST_DUE').count()
        suspended = GymSubscription.objects.filter(status='SUSPENDED').count()
        cancelled = GymSubscription.objects.filter(status='CANCELLED').count()
        
        # At risk: past due + expiring soon without auto-renew
        expiring_soon = GymSubscription.objects.filter(
            status='ACTIVE',
            auto_renew=False,
            current_period_end__lte=seven_days_future
        ).count()
        at_risk = past_due + expiring_soon
        
        # Churn rate (cancelled in last 30 days / total at start of period)
        cancelled_30d = GymSubscription.objects.filter(
            status='CANCELLED',
            updated_at__gte=thirty_days_ago
        ).count()
        
        total_start = active + past_due + suspended + cancelled_30d
        churn_rate = Decimal('0.0')
        if total_start > 0:
            churn_rate = Decimal(cancelled_30d / total_start * 100).quantize(Decimal('0.1'))
        
        return SubscriptionHealthStatus(
            total_active=active,
            total_past_due=past_due,
            total_suspended=suspended,
            total_cancelled=cancelled,
            at_risk_count=at_risk,
            churn_rate_30d=churn_rate
        )
    
    # ==================== Combined Dashboard ====================
    
    def get_health_dashboard(self) -> dict:
        """
        Get complete health dashboard data.
        Returns all health metrics in a single call.
        """
        return {
            'timestamp': timezone.now().isoformat(),
            'webhook': self.get_webhook_health().__dict__,
            'payments': self.get_payment_health().__dict__,
            'subscriptions': self.get_subscription_health().__dict__,
            'overall_status': self._calculate_overall_status()
        }
    
    def _calculate_overall_status(self) -> str:
        """
        Calculate overall system health status.
        Returns: 'healthy', 'warning', or 'critical'
        """
        webhook = self.get_webhook_health()
        payments = self.get_payment_health()
        subs = self.get_subscription_health()
        
        # Critical conditions
        if webhook.consecutive_failures >= 5:
            return 'critical'
        if payments.success_rate_7d < Decimal('80.0'):
            return 'critical'
        if subs.total_suspended > subs.total_active * Decimal('0.1'):
            return 'critical'
        
        # Warning conditions
        if webhook.consecutive_failures >= 2:
            return 'warning'
        if payments.success_rate_7d < Decimal('95.0'):
            return 'warning'
        if subs.churn_rate_30d > Decimal('5.0'):
            return 'warning'
        if subs.at_risk_count > 5:
            return 'warning'
        
        return 'healthy'
    
    # ==================== Invoice Analytics ====================
    
    def get_invoice_analytics(self, days: int = 30) -> dict:
        """Get invoice analytics for the specified period."""
        start_date = date.today() - timedelta(days=days)
        
        invoices = Invoice.objects.filter(created_at__date__gte=start_date)
        
        by_status = invoices.values('status').annotate(
            count=Count('id'),
            total=Sum('total_amount')
        )
        
        status_map = {item['status']: item for item in by_status}
        
        return {
            'period_days': days,
            'total_invoices': invoices.count(),
            'total_amount': invoices.aggregate(t=Sum('total_amount'))['t'] or Decimal('0'),
            'paid': {
                'count': status_map.get('PAID', {}).get('count', 0),
                'amount': status_map.get('PAID', {}).get('total', Decimal('0'))
            },
            'pending': {
                'count': status_map.get('PENDING', {}).get('count', 0),
                'amount': status_map.get('PENDING', {}).get('total', Decimal('0'))
            },
            'failed': {
                'count': status_map.get('FAILED', {}).get('count', 0),
                'amount': status_map.get('FAILED', {}).get('total', Decimal('0'))
            },
        }


# Singleton instance
health_monitor = HealthMonitorService()
