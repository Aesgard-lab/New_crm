"""
SaaS Billing Alert System.

Provides email notifications for critical billing events:
- Payment failures
- Subscriptions entering grace period
- Subscriptions about to expire
- Revenue anomalies (MRR drops)
- Webhook health issues
"""
from dataclasses import dataclass
from datetime import date, timedelta
from decimal import Decimal
from typing import Optional
import logging

from django.conf import settings
from django.core.mail import send_mail, EmailMultiAlternatives
from django.template.loader import render_to_string
from django.db.models import Sum, Count, Q
from django.utils import timezone

from .models import (
    GymSubscription, FranchiseSubscription, Invoice, 
    PaymentAttempt, BillingConfig
)
from organizations.models import Gym

logger = logging.getLogger(__name__)


@dataclass
class AlertConfig:
    """Configuration for alert thresholds."""
    mrr_drop_threshold_percent: Decimal = Decimal('10.0')  # Alert if MRR drops >10%
    expiring_soon_days: int = 7  # Alert for subscriptions expiring in X days
    failed_webhooks_threshold: int = 5  # Alert if X webhooks fail in a row
    payment_retry_threshold: int = 3  # Alert after X failed payment attempts


class SuperadminAlertService:
    """
    Service for sending alerts to superadmins about critical billing events.
    """
    
    def __init__(self):
        self.config = AlertConfig()
        self._billing_config: Optional[BillingConfig] = None
    
    @property
    def billing_config(self) -> BillingConfig:
        """Get cached billing config."""
        if self._billing_config is None:
            self._billing_config = BillingConfig.get_config()
        return self._billing_config
    
    def get_superadmin_emails(self) -> list[str]:
        """Get list of superadmin emails for notifications."""
        from accounts.models import User
        return list(
            User.objects.filter(
                is_superuser=True, 
                is_active=True
            ).values_list('email', flat=True)
        )
    
    def send_alert(
        self, 
        subject: str, 
        message: str, 
        level: str = 'warning',
        html_content: Optional[str] = None
    ) -> bool:
        """
        Send an alert email to all superadmins.
        
        Args:
            subject: Email subject
            message: Plain text message
            level: Alert level (info, warning, critical)
            html_content: Optional HTML version
            
        Returns:
            True if email sent successfully
        """
        recipients = self.get_superadmin_emails()
        if not recipients:
            logger.warning("No superadmin emails found for alert")
            return False
        
        # Add level emoji to subject
        level_emoji = {
            'info': 'ℹ️',
            'warning': '⚠️',
            'critical': '🚨'
        }
        full_subject = f"{level_emoji.get(level, '📢')} [SaaS] {subject}"
        
        try:
            if html_content:
                email = EmailMultiAlternatives(
                    subject=full_subject,
                    body=message,
                    from_email=settings.DEFAULT_FROM_EMAIL,
                    to=recipients
                )
                email.attach_alternative(html_content, "text/html")
                email.send()
            else:
                send_mail(
                    subject=full_subject,
                    message=message,
                    from_email=settings.DEFAULT_FROM_EMAIL,
                    recipient_list=recipients,
                    fail_silently=False
                )
            logger.info(f"Alert sent: {subject} to {len(recipients)} superadmins")
            return True
        except Exception as e:
            logger.error(f"Failed to send alert: {e}")
            return False
    
    # ==================== Payment Alerts ====================
    
    def alert_payment_failed(
        self, 
        gym: Gym, 
        invoice: Invoice, 
        failure_reason: str,
        attempt_number: int
    ):
        """Alert when a payment fails."""
        subject = f"Pago fallido: {gym.name}"
        
        message = f"""
PAGO FALLIDO - Intento #{attempt_number}

Gimnasio: {gym.name}
Factura: {invoice.invoice_number}
Importe: {invoice.total_amount}€
Razón: {failure_reason}

Estado actual de suscripción: {gym.subscription.get_status_display() if hasattr(gym, 'subscription') else 'N/A'}

Acciones recomendadas:
1. Contactar al cliente para actualizar método de pago
2. Verificar configuración de Stripe
3. Revisar si hay fraude

Dashboard: /superadmin/gym/{gym.id}/
"""
        
        level = 'critical' if attempt_number >= self.config.payment_retry_threshold else 'warning'
        self.send_alert(subject, message, level=level)
    
    def alert_subscription_past_due(self, gym: Gym, days_overdue: int):
        """Alert when subscription enters PAST_DUE status."""
        subject = f"Suscripción vencida: {gym.name} ({days_overdue} días)"
        
        grace_days = self.billing_config.grace_period_days
        days_until_suspension = max(0, grace_days - days_overdue)
        
        message = f"""
SUSCRIPCIÓN VENCIDA

Gimnasio: {gym.name}
Días vencidos: {days_overdue}
Días hasta suspensión: {days_until_suspension}
Plan: {gym.subscription.plan.name if hasattr(gym, 'subscription') else 'N/A'}

El gimnasio será suspendido automáticamente en {days_until_suspension} días si no paga.

Dashboard: /superadmin/gym/{gym.id}/
"""
        
        level = 'critical' if days_until_suspension <= 3 else 'warning'
        self.send_alert(subject, message, level=level)
    
    def alert_subscription_suspended(self, gym: Gym):
        """Alert when a subscription is suspended."""
        subject = f"Gimnasio suspendido: {gym.name}"
        
        message = f"""
🔒 GIMNASIO SUSPENDIDO

Gimnasio: {gym.name}
Plan: {gym.subscription.plan.name if hasattr(gym, 'subscription') else 'N/A'}
Motivo: Falta de pago tras periodo de gracia

El gimnasio ya no puede acceder al backoffice.
Los clientes finales tampoco pueden acceder.

Acciones:
1. Contactar al propietario del gimnasio
2. Gestionar reactivación si hay pago

Dashboard: /superadmin/gym/{gym.id}/
"""
        
        self.send_alert(subject, message, level='critical')
    
    # ==================== Expiration Alerts ====================
    
    def alert_subscriptions_expiring_soon(self) -> int:
        """
        Send alerts for subscriptions expiring soon.
        Returns number of alerts sent.
        """
        threshold_date = date.today() + timedelta(days=self.config.expiring_soon_days)
        
        expiring = GymSubscription.objects.filter(
            status='ACTIVE',
            auto_renew=False,
            current_period_end__lte=threshold_date,
            current_period_end__gte=date.today()
        ).select_related('gym', 'plan')
        
        if not expiring.exists():
            return 0
        
        subject = f"{expiring.count()} suscripciones expiran pronto"
        
        gyms_list = "\n".join([
            f"- {sub.gym.name}: expira {sub.current_period_end} ({sub.plan.name})"
            for sub in expiring
        ])
        
        message = f"""
SUSCRIPCIONES POR EXPIRAR (próximos {self.config.expiring_soon_days} días)

{gyms_list}

Estas suscripciones NO tienen renovación automática.
Contactar a los propietarios para renovar manualmente.
"""
        
        self.send_alert(subject, message, level='warning')
        return expiring.count()
    
    # ==================== Revenue Alerts ====================
    
    def alert_mrr_anomaly(self, previous_mrr: Decimal, current_mrr: Decimal):
        """Alert if MRR drops significantly."""
        if previous_mrr <= 0:
            return
        
        drop_percent = ((previous_mrr - current_mrr) / previous_mrr) * 100
        
        if drop_percent < self.config.mrr_drop_threshold_percent:
            return  # No significant drop
        
        subject = f"Caída de MRR: {drop_percent:.1f}%"
        
        message = f"""
⚠️ ANOMALÍA EN INGRESOS RECURRENTES

MRR anterior: {previous_mrr:.2f}€
MRR actual: {current_mrr:.2f}€
Caída: {drop_percent:.1f}%

Posibles causas:
- Cancelaciones de suscripciones
- Downgrade de planes
- Pagos fallidos

Revisar dashboard de métricas para más detalles.
"""
        
        self.send_alert(subject, message, level='critical')
    
    def calculate_current_mrr(self) -> Decimal:
        """Calculate current Monthly Recurring Revenue."""
        mrr = GymSubscription.objects.filter(
            status='ACTIVE',
            billing_frequency='MONTHLY'
        ).select_related('plan').aggregate(
            total=Sum('plan__price_monthly')
        )['total'] or Decimal('0.00')
        
        # Add yearly subscriptions converted to monthly
        yearly_monthly = GymSubscription.objects.filter(
            status='ACTIVE',
            billing_frequency='YEARLY'
        ).select_related('plan').aggregate(
            total=Sum('plan__price_yearly')
        )['total'] or Decimal('0.00')
        
        mrr += yearly_monthly / 12
        
        return mrr
    
    # ==================== System Health Alerts ====================
    
    def alert_webhook_failures(self, failure_count: int, last_error: str):
        """Alert on repeated webhook failures."""
        if failure_count < self.config.failed_webhooks_threshold:
            return
        
        subject = f"Fallos de webhook Stripe: {failure_count} consecutivos"
        
        message = f"""
🔴 FALLOS DE WEBHOOK DE STRIPE

Fallos consecutivos: {failure_count}
Último error: {last_error}

Los webhooks son críticos para:
- Procesar pagos
- Actualizar estados de suscripción
- Generar facturas

Acciones inmediatas:
1. Verificar configuración de webhook en Stripe Dashboard
2. Revisar logs del servidor
3. Verificar que el endpoint es accesible públicamente
4. Comprobar el webhook secret

Endpoint: /saas/webhooks/stripe/
"""
        
        self.send_alert(subject, message, level='critical')
    
    def alert_pending_invoices_summary(self) -> dict:
        """
        Daily summary of pending invoices.
        Returns summary stats.
        """
        pending = Invoice.objects.filter(status='PENDING')
        failed = Invoice.objects.filter(status='FAILED')
        
        pending_total = pending.aggregate(total=Sum('total_amount'))['total'] or Decimal('0.00')
        failed_total = failed.aggregate(total=Sum('total_amount'))['total'] or Decimal('0.00')
        
        stats = {
            'pending_count': pending.count(),
            'pending_total': pending_total,
            'failed_count': failed.count(),
            'failed_total': failed_total,
        }
        
        if pending.count() == 0 and failed.count() == 0:
            return stats  # No alert needed
        
        subject = f"Resumen diario: {pending.count()} pendientes, {failed.count()} fallidas"
        
        message = f"""
📊 RESUMEN DIARIO DE FACTURACIÓN

FACTURAS PENDIENTES: {pending.count()}
Total pendiente: {pending_total:.2f}€

FACTURAS FALLIDAS: {failed.count()}
Total fallido: {failed_total:.2f}€

Revisar dashboard para gestionar cobros.
"""
        
        level = 'critical' if failed.count() > 5 else 'info'
        self.send_alert(subject, message, level=level)
        
        return stats


# Singleton instance
alert_service = SuperadminAlertService()
