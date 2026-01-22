from django.db import models
from django.conf import settings
from django.utils.translation import gettext_lazy as _
from django.core.validators import MinValueValidator
from decimal import Decimal
import uuid


class SubscriptionPlan(models.Model):
    """
    Defines available SaaS subscription tiers for gyms.
    Each plan has specific modules enabled and usage limits.
    """
    
    BILLING_FREQUENCY_CHOICES = [
        ('MONTHLY', _('Mensual')),
        ('YEARLY', _('Anual')),
    ]
    
    # Basic Info
    name = models.CharField(max_length=100, help_text=_("Ej: Básico, Pro, Enterprise"))
    description = models.TextField(blank=True, help_text=_("Descripción del plan"))
    
    # Pricing
    price_monthly = models.DecimalField(
        max_digits=10, 
        decimal_places=2,
        validators=[MinValueValidator(Decimal('0.00'))],
        help_text=_("Precio mensual en EUR")
    )
    price_yearly = models.DecimalField(
        max_digits=10, 
        decimal_places=2,
        null=True,
        blank=True,
        validators=[MinValueValidator(Decimal('0.00'))],
        help_text=_("Precio anual en EUR (opcional, con descuento)")
    )
    
    # Module Permissions
    module_pos = models.BooleanField(default=True, verbose_name=_("TPV / Point of Sale"))
    module_calendar = models.BooleanField(default=True, verbose_name=_("Calendario de Clases"))
    module_marketing = models.BooleanField(default=False, verbose_name=_("Marketing y Campañas"))
    module_reporting = models.BooleanField(default=False, verbose_name=_("Reportes Avanzados"))
    module_client_portal = models.BooleanField(default=True, verbose_name=_("Portal de Cliente"))
    module_public_portal = models.BooleanField(default=False, verbose_name=_("Portal Público"))
    module_automations = models.BooleanField(default=False, verbose_name=_("Automatizaciones"))
    module_routines = models.BooleanField(default=False, verbose_name=_("Rutinas de Entrenamiento"))
    module_gamification = models.BooleanField(default=False, verbose_name=_("Gamificación"))
    
    # Limits (null = unlimited)
    max_members = models.PositiveIntegerField(
        null=True, 
        blank=True,
        help_text=_("Máximo de socios activos (vacío = ilimitado)")
    )
    max_staff = models.PositiveIntegerField(
        null=True,
        blank=True,
        help_text=_("Máximo de usuarios staff (vacío = ilimitado)")
    )
    max_locations = models.PositiveIntegerField(
        null=True,
        blank=True,
        help_text=_("Máximo de ubicaciones para franquicias (vacío = ilimitado)")
    )
    
    # Special Flags
    is_demo = models.BooleanField(
        default=False,
        help_text=_("Plan demo/prueba gratuito (no se cobra)")
    )
    is_active = models.BooleanField(
        default=True,
        help_text=_("Puede ser asignado a nuevos gimnasios")
    )
    display_order = models.IntegerField(default=0, help_text=_("Orden de visualización"))
    
    # Stripe Integration
    stripe_product_id = models.CharField(max_length=100, blank=True, help_text=_("ID del producto en Stripe"))
    stripe_price_monthly_id = models.CharField(max_length=100, blank=True, help_text=_("ID del precio mensual en Stripe"))
    stripe_price_yearly_id = models.CharField(max_length=100, blank=True, help_text=_("ID del precio anual en Stripe"))
    
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    class Meta:
        verbose_name = _("Plan de Suscripción")
        verbose_name_plural = _("Planes de Suscripción")
        ordering = ['display_order', 'price_monthly']
    
    def __str__(self):
        demo_label = " 🎁 Demo" if self.is_demo else ""
        return f"{self.name} - {self.price_monthly}€/mes{demo_label}"
    
    def get_enabled_modules(self):
        """Returns list of enabled module names"""
        modules = []
        if self.module_pos: modules.append("POS")
        if self.module_calendar: modules.append("Calendario")
        if self.module_marketing: modules.append("Marketing")
        if self.module_reporting: modules.append("Reportes")
        if self.module_client_portal: modules.append("Portal Cliente")
        if self.module_public_portal: modules.append("Portal Público")
        if self.module_automations: modules.append("Automatizaciones")
        if self.module_routines: modules.append("Rutinas")
        if self.module_gamification: modules.append("Gamificación")
        return modules


class GymSubscription(models.Model):
    """
    Links a gym to their active subscription plan.
    Manages billing cycle, payment status, and Stripe integration.
    """
    
    STATUS_CHOICES = [
        ('ACTIVE', _('Activa')),
        ('PAST_DUE', _('Pago Vencido')),
        ('SUSPENDED', _('Suspendida')),
        ('CANCELLED', _('Cancelada')),
    ]
    
    BILLING_FREQUENCY_CHOICES = [
        ('MONTHLY', _('Mensual')),
        ('YEARLY', _('Anual')),
    ]
    
    gym = models.OneToOneField(
        'organizations.Gym',
        on_delete=models.CASCADE,
        related_name='subscription'
    )
    plan = models.ForeignKey(
        SubscriptionPlan,
        on_delete=models.PROTECT,
        related_name='gym_subscriptions'
    )
    
    # Status
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='ACTIVE')
    billing_frequency = models.CharField(max_length=20, choices=BILLING_FREQUENCY_CHOICES, default='MONTHLY')
    
    # Billing Cycle
    current_period_start = models.DateField(help_text=_("Inicio del período actual"))
    current_period_end = models.DateField(help_text=_("Fin del período actual"))
    
    # Stripe Integration
    stripe_subscription_id = models.CharField(max_length=100, blank=True, help_text=_("ID de suscripción en Stripe"))
    stripe_customer_id = models.CharField(max_length=100, blank=True, help_text=_("ID de cliente en Stripe"))
    
    # Payment Method (for display)
    payment_method_last4 = models.CharField(max_length=4, blank=True, help_text=_("Últimos 4 dígitos de la tarjeta"))
    payment_method_brand = models.CharField(max_length=20, blank=True, help_text=_("Visa, Mastercard, etc."))
    
    # Control
    auto_renew = models.BooleanField(default=True, help_text=_("Renovar automáticamente"))
    suspension_date = models.DateField(null=True, blank=True, help_text=_("Fecha de suspensión (para periodo de gracia)"))
    
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    class Meta:
        verbose_name = _("Suscripción de Gimnasio")
        verbose_name_plural = _("Suscripciones de Gimnasios")
    
    def __str__(self):
        return f"{self.gym.name} - {self.plan.name} ({self.get_status_display()})"
    
    def is_past_grace_period(self, grace_days=15):
        """Check if subscription is past grace period"""
        if self.status != 'PAST_DUE' or not self.suspension_date:
            return False
        from datetime import date
        days_past = (date.today() - self.suspension_date).days
        return days_past > grace_days


class FranchiseSubscription(models.Model):
    """
    Optional: Franchise-level subscriptions that cover multiple gyms.
    Franchise owner pays once for all their locations.
    """
    
    STATUS_CHOICES = [
        ('ACTIVE', _('Activa')),
        ('PAST_DUE', _('Pago Vencido')),
        ('SUSPENDED', _('Suspendida')),
        ('CANCELLED', _('Cancelada')),
    ]
    
    franchise = models.OneToOneField(
        'organizations.Franchise',
        on_delete=models.CASCADE,
        related_name='subscription'
    )
    plan = models.ForeignKey(
        SubscriptionPlan,
        on_delete=models.PROTECT,
        related_name='franchise_subscriptions'
    )
    
    # Which gyms are covered by this subscription
    covered_gyms = models.ManyToManyField(
        'organizations.Gym',
        related_name='franchise_subscription',
        blank=True,
        help_text=_("Gimnasios cubiertos por esta suscripción de franquicia")
    )
    
    # Status and billing (same as GymSubscription)
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='ACTIVE')
    billing_frequency = models.CharField(max_length=20, default='MONTHLY')
    current_period_start = models.DateField()
    current_period_end = models.DateField()
    
    # Stripe
    stripe_subscription_id = models.CharField(max_length=100, blank=True)
    stripe_customer_id = models.CharField(max_length=100, blank=True)
    payment_method_last4 = models.CharField(max_length=4, blank=True)
    payment_method_brand = models.CharField(max_length=20, blank=True)
    
    auto_renew = models.BooleanField(default=True)
    suspension_date = models.DateField(null=True, blank=True)
    
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    class Meta:
        verbose_name = _("Suscripción de Franquicia")
        verbose_name_plural = _("Suscripciones de Franquicias")
    
    def __str__(self):
        return f"{self.franchise.name} - {self.plan.name}"


class Invoice(models.Model):
    """
    Payment invoices for both gym and franchise subscriptions.
    Stores invoice data and PDF files.
    """
    
    STATUS_CHOICES = [
        ('PENDING', _('Pendiente')),
        ('PAID', _('Pagada')),
        ('FAILED', _('Fallida')),
        ('REFUNDED', _('Reembolsada')),
    ]
    
    # Who is being invoiced (one or the other)
    gym = models.ForeignKey(
        'organizations.Gym',
        on_delete=models.CASCADE,
        null=True,
        blank=True,
        related_name='invoices'
    )
    franchise = models.ForeignKey(
        'organizations.Franchise',
        on_delete=models.CASCADE,
        null=True,
        blank=True,
        related_name='invoices'
    )
    
    # Invoice Details
    invoice_number = models.CharField(max_length=50, unique=True, help_text=_("Número de factura único"))
    
    # Amounts
    amount = models.DecimalField(max_digits=10, decimal_places=2, help_text=_("Importe base"))
    tax_amount = models.DecimalField(max_digits=10, decimal_places=2, default=0, help_text=_("IVA u otros impuestos"))
    total_amount = models.DecimalField(max_digits=10, decimal_places=2, help_text=_("Total a pagar"))
    currency = models.CharField(max_length=3, default='EUR')
    
    # Status
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='PENDING')
    
    # Dates
    issue_date = models.DateField(help_text=_("Fecha de emisión"))
    due_date = models.DateField(help_text=_("Fecha de vencimiento"))
    paid_date = models.DateField(null=True, blank=True, help_text=_("Fecha de pago"))
    
    # Stripe
    stripe_invoice_id = models.CharField(max_length=100, blank=True)
    stripe_payment_intent_id = models.CharField(max_length=100, blank=True)
    
    # PDF
    pdf_file = models.FileField(upload_to='invoices/%Y/%m/', blank=True, null=True)
    
    # Description
    description = models.TextField(blank=True, help_text=_("Concepto de la factura"))
    
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    class Meta:
        verbose_name = _("Factura")
        verbose_name_plural = _("Facturas")
        ordering = ['-issue_date']
    
    def __str__(self):
        entity = self.gym.name if self.gym else self.franchise.name
        return f"{self.invoice_number} - {entity} - {self.total_amount}€"
    
    def generate_invoice_number(self):
        """Auto-generate unique invoice number"""
        from datetime import date
        today = date.today()
        prefix = f"INV-{today.year}{today.month:02d}"
        
        # Find last invoice this month
        last_invoice = Invoice.objects.filter(
            invoice_number__startswith=prefix
        ).order_by('-invoice_number').first()
        
        if last_invoice:
            last_num = int(last_invoice.invoice_number.split('-')[-1])
            new_num = last_num + 1
        else:
            new_num = 1
        
        return f"{prefix}-{new_num:04d}"


class PaymentAttempt(models.Model):
    """
    Tracks payment attempts for failed/retrying payments.
    Used for retry logic and debugging.
    """
    
    STATUS_CHOICES = [
        ('FAILED', _('Fallido')),
        ('RETRYING', _('Reintentando')),
        ('SUCCEEDED', _('Exitoso')),
    ]
    
    invoice = models.ForeignKey(
        Invoice,
        on_delete=models.CASCADE,
        related_name='payment_attempts'
    )
    
    # Subscription (for context)
    gym_subscription = models.ForeignKey(
        GymSubscription,
        on_delete=models.CASCADE,
        null=True,
        blank=True,
        related_name='payment_attempts'
    )
    franchise_subscription = models.ForeignKey(
        FranchiseSubscription,
        on_delete=models.CASCADE,
        null=True,
        blank=True,
        related_name='payment_attempts'
    )
    
    # Stripe
    stripe_payment_intent_id = models.CharField(max_length=100, blank=True)
    
    # Details
    amount = models.DecimalField(max_digits=10, decimal_places=2)
    status = models.CharField(max_length=20, choices=STATUS_CHOICES)
    failure_reason = models.TextField(blank=True, help_text=_("Razón del fallo según Stripe"))
    
    # Timing
    attempted_at = models.DateTimeField(auto_now_add=True)
    next_retry = models.DateTimeField(null=True, blank=True, help_text=_("Próximo reintento programado"))
    
    class Meta:
        verbose_name = _("Intento de Pago")
        verbose_name_plural = _("Intentos de Pago")
        ordering = ['-attempted_at']
    
    def __str__(self):
        return f"{self.invoice.invoice_number} - {self.get_status_display()} - {self.attempted_at}"


class BillingConfig(models.Model):
    """
    Singleton model for superadmin billing configuration.
    Stores company info and encrypted Stripe keys.
    """
    
    # Company Info (for invoices)
    company_name = models.CharField(max_length=200, help_text=_("Razón social de tu empresa"))
    company_tax_id = models.CharField(max_length=50, help_text=_("CIF/NIF"))
    company_address = models.TextField(help_text=_("Dirección fiscal completa"))
    company_email = models.EmailField(help_text=_("Email de soporte"))
    company_phone = models.CharField(max_length=20, blank=True)
    company_logo = models.ImageField(upload_to='billing/company/', blank=True, null=True)
    
    # System Branding (White Label)
    system_logo = models.ImageField(
        upload_to='system/branding/',
        blank=True,
        null=True,
        help_text=_("Logo del sistema para el login del backoffice (marca blanca)")
    )
    system_name = models.CharField(
        max_length=100,
        default='New CRM',
        help_text=_("Nombre del sistema para mostrar en login")
    )
    
    # Stripe Keys (should be encrypted in production)
    stripe_publishable_key = models.CharField(
        max_length=200,
        blank=True,
        help_text=_("Clave pública de Stripe (pk_...)")
    )
    stripe_secret_key = models.CharField(
        max_length=200,
        blank=True,
        help_text=_("Clave secreta de Stripe (sk_...) - ENCRIPTADA")
    )
    stripe_webhook_secret = models.CharField(
        max_length=200,
        blank=True,
        help_text=_("Secret del webhook de Stripe (whsec_...)")
    )
    
    # Grace Period Settings
    grace_period_days = models.PositiveIntegerField(
        default=15,
        help_text=_("Días de gracia antes de suspender por falta de pago")
    )
    enable_auto_suspension = models.BooleanField(
        default=True,
        help_text=_("Suspender automáticamente tras el periodo de gracia")
    )
    
    # Email Templates
    payment_failed_email_subject = models.CharField(max_length=200, default=_("Problema con tu pago"))
    payment_failed_email_body = models.TextField(
        default=_("Tu pago ha fallado. Por favor, actualiza tu método de pago."),
        help_text=_("Plantilla de email para pagos fallidos")
    )
    
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    class Meta:
        verbose_name = _("Configuración de Facturación")
        verbose_name_plural = _("Configuración de Facturación")
    
    def __str__(self):
        return f"Billing Config - {self.company_name}"
    
    def save(self, *args, **kwargs):
        # Ensure singleton
        self.pk = 1
        super().save(*args, **kwargs)
    
    @classmethod
    def get_config(cls):
        """Get or create singleton instance"""
        config, created = cls.objects.get_or_create(pk=1)
        return config


class AuditLog(models.Model):
    """
    Logs all superadmin actions for security and compliance.
    Tracks gym/franchise creation, plan changes, god mode access, etc.
    """
    
    ACTION_CHOICES = [
        ('CREATE_GYM', _('Crear Gimnasio')),
        ('EDIT_GYM', _('Editar Gimnasio')),
        ('DELETE_GYM', _('Eliminar Gimnasio')),
        ('CREATE_FRANCHISE', _('Crear Franquicia')),
        ('EDIT_FRANCHISE', _('Editar Franquicia')),
        ('CHANGE_PLAN', _('Cambiar Plan')),
        ('SUSPEND_GYM', _('Suspender Gimnasio')),
        ('REACTIVATE_GYM', _('Reactivar Gimnasio')),
        ('GOD_MODE_LOGIN', _('Acceso Modo Dios')),
        ('UPDATE_BILLING_CONFIG', _('Actualizar Config Facturación')),
        ('MANUAL_INVOICE', _('Factura Manual')),
        ('REFUND', _('Reembolso')),
    ]
    
    # Who did it
    superadmin = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        related_name='saas_audit_logs'  # Changed from 'audit_logs' to avoid clash with staff.AuditLog
    )
    
    # What action
    action = models.CharField(max_length=50, choices=ACTION_CHOICES)
    description = models.TextField(help_text=_("Descripción detallada de la acción"))
    
    # Where (target)
    target_gym = models.ForeignKey(
        'organizations.Gym',
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='saas_billing_logs'  # Changed from 'audit_logs' to avoid clash with staff.AuditLog
    )
    target_franchise = models.ForeignKey(
        'organizations.Franchise',
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='saas_billing_logs'  # SaaS specific logs
    )
    
    # Security Info
    ip_address = models.GenericIPAddressField(help_text=_("IP del superadmin"))
    user_agent = models.TextField(blank=True, help_text=_("User Agent del navegador"))
    
    created_at = models.DateTimeField(auto_now_add=True)
    
    class Meta:
        verbose_name = _("Log de Auditoría")
        verbose_name_plural = _("Logs de Auditoría")
        ordering = ['-created_at']
        indexes = [
            models.Index(fields=['-created_at']),
            models.Index(fields=['superadmin', '-created_at']),
        ]
    
    def __str__(self):
        admin_name = self.superadmin.get_full_name() if self.superadmin else "Sistema"
        return f"{self.get_action_display()} - {admin_name} - {self.created_at}"
