"""
SaaS Billing Scheduled Tasks.

Background tasks for subscription management:
- Check and suspend overdue subscriptions
- Send payment reminders
- Generate recurring invoices
- Monitor webhook health
- Calculate and store MRR metrics

These tasks should be run via cron, Celery, or Django-Q.
"""
from datetime import date, timedelta
from decimal import Decimal
from typing import Optional
import logging

from django.db import transaction
from django.db.models import Sum, Count, Q, F
from django.utils import timezone

from .models import (
    GymSubscription, FranchiseSubscription, Invoice,
    PaymentAttempt, BillingConfig, AuditLog
)
from .alerts import alert_service
from organizations.models import Gym

logger = logging.getLogger(__name__)


class SubscriptionTaskService:
    """
    Service for running scheduled subscription management tasks.
    """
    
    def __init__(self):
        self._billing_config: Optional[BillingConfig] = None
    
    @property
    def billing_config(self) -> BillingConfig:
        """Get cached billing config."""
        if self._billing_config is None:
            self._billing_config = BillingConfig.get_config()
        return self._billing_config
    
    # ==================== Overdue Processing ====================
    
    @transaction.atomic
    def process_overdue_subscriptions(self) -> dict:
        """
        Check for overdue subscriptions and update their status.
        
        Returns summary of actions taken.
        """
        today = date.today()
        grace_days = self.billing_config.grace_period_days
        
        stats = {
            'checked': 0,
            'marked_past_due': 0,
            'suspended': 0,
            'alerts_sent': 0,
        }
        
        # Find active subscriptions past their period end
        active_overdue = GymSubscription.objects.filter(
            status='ACTIVE',
            current_period_end__lt=today
        ).select_related('gym', 'plan')
        
        for subscription in active_overdue:
            stats['checked'] += 1
            days_overdue = (today - subscription.current_period_end).days
            
            # Mark as PAST_DUE
            subscription.status = 'PAST_DUE'
            subscription.suspension_date = subscription.current_period_end
            subscription.save(update_fields=['status', 'suspension_date', 'updated_at'])
            
            stats['marked_past_due'] += 1
            
            # Send alert
            alert_service.alert_subscription_past_due(subscription.gym, days_overdue)
            stats['alerts_sent'] += 1
            
            logger.info(f"Subscription {subscription.gym.name} marked as PAST_DUE")
        
        # Check PAST_DUE subscriptions for suspension
        if self.billing_config.enable_auto_suspension:
            past_due = GymSubscription.objects.filter(
                status='PAST_DUE',
                suspension_date__isnull=False
            ).select_related('gym', 'plan')
            
            for subscription in past_due:
                days_past = (today - subscription.suspension_date).days
                
                if days_past > grace_days:
                    # Suspend the subscription
                    subscription.status = 'SUSPENDED'
                    subscription.save(update_fields=['status', 'updated_at'])
                    
                    stats['suspended'] += 1
                    
                    # Log the action
                    AuditLog.objects.create(
                        action='SUSPEND_GYM',
                        description=f"Auto-suspended after {days_past} days overdue",
                        target_gym=subscription.gym,
                        ip_address='system'
                    )
                    
                    # Send alert
                    alert_service.alert_subscription_suspended(subscription.gym)
                    stats['alerts_sent'] += 1
                    
                    logger.warning(f"Subscription {subscription.gym.name} SUSPENDED")
        
        return stats
    
    # ==================== Reminder Emails ====================
    
    def send_payment_reminders(self) -> dict:
        """
        Send reminder emails for upcoming and overdue payments.
        
        Returns summary of reminders sent.
        """
        today = date.today()
        
        stats = {
            'upcoming_reminders': 0,
            'overdue_reminders': 0,
        }
        
        # Upcoming: 7 days before expiration
        upcoming_threshold = today + timedelta(days=7)
        upcoming = GymSubscription.objects.filter(
            status='ACTIVE',
            billing_mode='AUTO',
            current_period_end__lte=upcoming_threshold,
            current_period_end__gt=today
        ).select_related('gym', 'plan')
        
        for subscription in upcoming:
            days_until = (subscription.current_period_end - today).days
            self._send_upcoming_reminder(subscription, days_until)
            stats['upcoming_reminders'] += 1
        
        # Overdue: PAST_DUE subscriptions
        past_due = GymSubscription.objects.filter(
            status='PAST_DUE'
        ).select_related('gym', 'plan')
        
        for subscription in past_due:
            days_overdue = (today - subscription.current_period_end).days
            # Send reminder every 3 days
            if days_overdue % 3 == 0:
                self._send_overdue_reminder(subscription, days_overdue)
                stats['overdue_reminders'] += 1
        
        return stats
    
    def _send_upcoming_reminder(self, subscription: GymSubscription, days_until: int):
        """Send email reminder for upcoming payment."""
        from django.core.mail import send_mail
        from django.conf import settings
        
        gym = subscription.gym
        subject = f"Recordatorio: Tu suscripción se renueva en {days_until} días"
        
        message = f"""
Hola,

Te recordamos que la suscripción de {gym.name} se renovará automáticamente en {days_until} días.

Plan: {subscription.plan.name}
Fecha de renovación: {subscription.current_period_end}
Importe: {subscription.plan.price_monthly if subscription.billing_frequency == 'MONTHLY' else subscription.plan.price_yearly}€

Si deseas modificar tu plan o método de pago, accede a tu dashboard de facturación.

Saludos,
{self.billing_config.company_name}
"""
        
        try:
            send_mail(
                subject=subject,
                message=message,
                from_email=settings.DEFAULT_FROM_EMAIL,
                recipient_list=[gym.email],
                fail_silently=True
            )
            logger.info(f"Upcoming reminder sent to {gym.name}")
        except Exception as e:
            logger.error(f"Failed to send reminder to {gym.name}: {e}")
    
    def _send_overdue_reminder(self, subscription: GymSubscription, days_overdue: int):
        """Send email reminder for overdue payment."""
        from django.core.mail import send_mail
        from django.conf import settings
        
        gym = subscription.gym
        grace_days = self.billing_config.grace_period_days
        days_until_suspension = max(0, grace_days - days_overdue)
        
        subject = f"⚠️ Pago vencido: {days_overdue} días - Acción requerida"
        
        message = f"""
URGENTE: Pago pendiente

Hola,

Tu suscripción de {gym.name} tiene un pago vencido de {days_overdue} días.

Plan: {subscription.plan.name}
Fecha de vencimiento: {subscription.current_period_end}

⚠️ IMPORTANTE: Tu cuenta será suspendida en {days_until_suspension} días si no regularizas el pago.

Para evitar la suspensión:
1. Accede a tu dashboard de facturación
2. Actualiza tu método de pago
3. O contacta con soporte

Saludos,
{self.billing_config.company_name}
"""
        
        try:
            send_mail(
                subject=subject,
                message=message,
                from_email=settings.DEFAULT_FROM_EMAIL,
                recipient_list=[gym.email],
                fail_silently=True
            )
            logger.info(f"Overdue reminder sent to {gym.name}")
        except Exception as e:
            logger.error(f"Failed to send overdue reminder to {gym.name}: {e}")
    
    # ==================== Invoice Generation ====================
    
    @transaction.atomic
    def generate_pending_invoices(self) -> dict:
        """
        Generate invoices for subscriptions due for renewal.
        
        Returns summary of invoices created.
        """
        today = date.today()
        
        stats = {
            'invoices_created': 0,
            'total_amount': Decimal('0.00'),
        }
        
        # Find subscriptions that need invoicing (period ends today or before, still active)
        due_for_renewal = GymSubscription.objects.filter(
            status='ACTIVE',
            auto_renew=True,
            current_period_end__lte=today
        ).select_related('gym', 'plan')
        
        for subscription in due_for_renewal:
            # Check if invoice already exists for this period
            existing = Invoice.objects.filter(
                gym=subscription.gym,
                issue_date=today,
                status__in=['PENDING', 'PAID']
            ).exists()
            
            if existing:
                continue
            
            # Calculate amount
            if subscription.billing_frequency == 'MONTHLY':
                amount = subscription.plan.price_monthly
            else:
                amount = subscription.plan.price_yearly or (subscription.plan.price_monthly * 12)
            
            # Create invoice
            invoice = Invoice(
                gym=subscription.gym,
                amount=amount,
                tax_amount=amount * Decimal('0.21'),  # 21% IVA
                total_amount=amount * Decimal('1.21'),
                issue_date=today,
                due_date=today + timedelta(days=7),
                description=f"Suscripción {subscription.plan.name} - {subscription.get_billing_frequency_display()}"
            )
            invoice.invoice_number = invoice.generate_invoice_number()
            invoice.save()
            
            stats['invoices_created'] += 1
            stats['total_amount'] += invoice.total_amount
            
            logger.info(f"Invoice {invoice.invoice_number} created for {subscription.gym.name}")
        
        return stats
    
    # ==================== MRR Tracking ====================
    
    def calculate_and_store_mrr(self) -> dict:
        """
        Calculate current MRR and compare with previous.
        Triggers alert if significant change detected.
        
        Returns MRR metrics.
        """
        current_mrr = alert_service.calculate_current_mrr()
        
        # Get previous MRR from cache or calculate approximation
        # In production, this should be stored in a metrics table
        from django.core.cache import cache
        previous_mrr = cache.get('saas_previous_mrr', current_mrr)
        
        metrics = {
            'current_mrr': current_mrr,
            'previous_mrr': previous_mrr,
            'change': current_mrr - previous_mrr,
            'change_percent': ((current_mrr - previous_mrr) / previous_mrr * 100) if previous_mrr > 0 else Decimal('0'),
        }
        
        # Check for significant drop
        if previous_mrr > current_mrr:
            alert_service.alert_mrr_anomaly(previous_mrr, current_mrr)
        
        # Store current as previous for next check
        cache.set('saas_previous_mrr', current_mrr, timeout=86400 * 7)  # 7 days
        
        return metrics
    
    # ==================== Daily Summary ====================
    
    def run_daily_tasks(self) -> dict:
        """
        Run all daily maintenance tasks.
        
        Returns combined summary of all tasks.
        """
        logger.info("Starting daily SaaS billing tasks...")
        
        results = {
            'timestamp': timezone.now().isoformat(),
            'overdue': self.process_overdue_subscriptions(),
            'reminders': self.send_payment_reminders(),
            'invoices': self.generate_pending_invoices(),
            'mrr': self.calculate_and_store_mrr(),
            'pending_summary': alert_service.alert_pending_invoices_summary(),
            'expiring': alert_service.alert_subscriptions_expiring_soon(),
        }
        
        logger.info(f"Daily tasks completed: {results}")
        return results


# Singleton instance
task_service = SubscriptionTaskService()


# ==================== Management Command Helpers ====================

def run_daily_billing_tasks():
    """Entry point for cron/celery."""
    return task_service.run_daily_tasks()


def process_overdue():
    """Entry point for overdue processing only."""
    return task_service.process_overdue_subscriptions()


def send_reminders():
    """Entry point for reminders only."""
    return task_service.send_payment_reminders()
