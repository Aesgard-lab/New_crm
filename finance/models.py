from django.db import models
from django.utils.translation import gettext_lazy as _
from django.utils import timezone
from django.conf import settings
from organizations.models import Gym

class TaxRate(models.Model):
    """
    Centralized tax rates (optional usage for now, ensuring future compatibility).
    """
    gym = models.ForeignKey(Gym, on_delete=models.CASCADE, related_name='tax_rates', default=1)
    name = models.CharField(_("Nombre del Impuesto"), max_length=50, help_text=_("Ej: IVA 21%"))
    rate_percent = models.DecimalField(_("Porcentaje"), max_digits=5, decimal_places=2, help_text=_("Ej: 21.00"))
    is_active = models.BooleanField(_("Activo"), default=True)

    def __str__(self):
        return f"{self.name} ({self.rate_percent}%)"

    class Meta:
        verbose_name = _("Impuesto")
        verbose_name_plural = _("Impuestos")

class PaymentMethod(models.Model):
    """
    Configurable payment methods (Cash, Card, Transfer, Stripe, etc.)
    """
    GATEWAY_CHOICES = [
        ('NONE', _('Sin pasarela (Efectivo/Manual)')),
        ('STRIPE', _('Stripe')),
        ('REDSYS', _('Redsys')),
        ('PAYPAL', _('PayPal')),
    ]
    
    gym = models.ForeignKey(Gym, on_delete=models.CASCADE, related_name='payment_methods', default=1)
    name = models.CharField(_("Nombre"), max_length=50) # Efectivo, Tarjeta, Bizum...
    description = models.CharField(_("Descripción"), max_length=255, blank=True)
    is_cash = models.BooleanField(_("Control de Caja"), default=False, 
        help_text=_("Si se marca, este método requiere una Sesión de Caja abierta y suma al efectivo físico."))
    is_active = models.BooleanField(_("Activo"), default=True)
    
    # Online availability
    available_for_online = models.BooleanField(_("Disponible para compra online"), default=False,
        help_text=_("Si se marca, este método estará disponible en el portal público"))
    display_order = models.IntegerField(_("Orden de visualización"), default=0)
    
    # Payment gateway integration
    gateway = models.CharField(_("Pasarela de pago"), max_length=20, choices=GATEWAY_CHOICES, default='NONE')
    
    # For future integrations:
    provider_code = models.CharField(_("Código Proveedor"), max_length=50, blank=True, null=True,
        help_text=_("ej: 'stripe_terminal', 'redsys', etc."))

    def __str__(self):
        return self.name

    class Meta:
        verbose_name = _("Método de Pago")
        verbose_name_plural = _("Métodos de Pago")
        ordering = ['display_order', 'name']

class CashSession(models.Model):
    """
    Represents a Shift or Day of 'Cash Drawer' (Arqueo).
    """
    gym = models.ForeignKey(Gym, on_delete=models.CASCADE, related_name='cash_sessions', default=1)
    opened_by = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.PROTECT, related_name='opened_sessions')
    closed_by = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.PROTECT, related_name='closed_sessions', null=True, blank=True)
    
    opened_at = models.DateTimeField(_("Apertura"), auto_now_add=True)
    closed_at = models.DateTimeField(_("Cierre"), null=True, blank=True)
    
    opening_balance = models.DecimalField(_("Fondo Inicial"), max_digits=10, decimal_places=2, default=0.00)
    
    # Financials at close
    total_cash_sales = models.DecimalField(_("Ventas Efectivo Sistema"), max_digits=10, decimal_places=2, default=0.00, help_text=_("Calculado automáticamente"))
    total_cash_withdrawals = models.DecimalField(_("Retiradas"), max_digits=10, decimal_places=2, default=0.00)
    total_cash_additions = models.DecimalField(_("Ingresos Extra"), max_digits=10, decimal_places=2, default=0.00)
    
    expected_balance = models.DecimalField(_("Esperado en Caja"), max_digits=10, decimal_places=2, default=0.00)
    actual_balance = models.DecimalField(_("Contado Real (Arqueo)"), max_digits=10, decimal_places=2, null=True, blank=True)
    discrepancy = models.DecimalField(_("Descuadre"), max_digits=10, decimal_places=2, null=True, blank=True)
    
    notes = models.TextField(_("Notas de Cierre"), blank=True)
    is_closed = models.BooleanField(_("Cerrada"), default=False)

    class Meta:
        verbose_name = _("Sesión de Caja")
        verbose_name_plural = _("Sesiones de Caja")
        ordering = ['-opened_at']

    def calculate_expected(self):
        """Helper to update expected balance"""
        self.expected_balance = self.opening_balance + self.total_cash_sales + self.total_cash_additions - self.total_cash_withdrawals

    def save(self, *args, **kwargs):
        self.calculate_expected()
        if self.actual_balance is not None:
            self.discrepancy = self.actual_balance - self.expected_balance
        super().save(*args, **kwargs)

class FinanceSettings(models.Model):
    """
    Singleton-like Settings for Finance per Gym (Stripe, Currency, etc.)
    """
    gym = models.OneToOneField(Gym, on_delete=models.CASCADE, related_name='finance_settings')
    
    # Stripe Configuration
    stripe_public_key = models.CharField(_("Stripe Public Key"), max_length=255, blank=True)
    stripe_secret_key = models.CharField(_("Stripe Secret Key"), max_length=255, blank=True)
    
    # Redsys
    redsys_merchant_code = models.CharField(_("FUC (Código de Comercio)"), max_length=255, blank=True)
    redsys_merchant_terminal = models.CharField(_("Terminal"), max_length=10, default="001", blank=True)
    redsys_secret_key = models.CharField(_("Clave Secreta (clave256)"), max_length=255, blank=True)
    redsys_environment = models.CharField(_("Entorno"), max_length=10, choices=[('TEST', 'Pruebas / Sandbox'), ('REAL', 'Producción / Real')], default='TEST') # TEST (sis-t) or REAL (sis)
    
    # Currency
    currency = models.CharField(_("Moneda Principal"), max_length=3, default='EUR', help_text=_("Ej: EUR, USD"))

    # Portal permissions
    allow_client_delete_card = models.BooleanField(default=False, help_text="Permitir que el cliente elimine sus tarjetas guardadas desde la app.")
    allow_client_pay_next_fee = models.BooleanField(default=False, help_text="Permitir que el cliente adelante/pague su siguiente cuota desde la app.")

    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        verbose_name = _("Configuración Financiera")
        verbose_name_plural = _("Configuraciones Financieras")

    def __str__(self):
        return f"Configuración Financiera de {self.gym.name}"

class ClientRedsysToken(models.Model):
    """
    Stores Redsys 'Reference' (Order ID of the initial auth) for recurring payments (Pago por Referencia).
    """
    client = models.ForeignKey('clients.Client', on_delete=models.CASCADE, related_name='redsys_tokens')
    token = models.CharField(_("Token / Referencia"), max_length=100, help_text="Suele ser el Ds_Order de la primera operación")
    card_brand = models.CharField(_("Marca"), max_length=50, blank=True) # VISA, MASTERCARD
    card_number = models.CharField(_("Número Enmascarado"), max_length=20, blank=True) # **** **** **** 1234
    expiration = models.CharField(_("Caducidad"), max_length=10, blank=True) # YYMM
    
    created_at = models.DateTimeField(auto_now_add=True)
    
    def __str__(self):
        return f"{self.card_brand} {self.card_number} ({self.client})"

    class Meta:
        verbose_name = _("Token Redsys Cliente")
        verbose_name_plural = _("Tokens Redsys Cliente")

class PosDevice(models.Model):
    """
    Hardware devices: Stripe Terminals, Printers, Turnstiles.
    """
    msg_types = [
        ('STRIPE_READER', 'Lector Tartjetas (Stripe Terminal)'),
        ('PRINTER_NETWORK', 'Impresora Térmica (Red)'),
        ('TURNSTILE', 'Torno de Acceso'),
    ]
    
    gym = models.ForeignKey(Gym, on_delete=models.CASCADE, related_name='devices')
    name = models.CharField(_("Nombre del Dispositivo"), max_length=100, help_text="Ej: Recepción Principal")
    device_type = models.CharField(max_length=20, choices=msg_types)
    identifier = models.CharField(_("Identificador / IP"), max_length=255, help_text="Serial Number (Stripe) o IP (Impresora)")
    
    is_active = models.BooleanField(default=True)
    
    created_at = models.DateTimeField(auto_now_add=True)
    
    def __str__(self):
        return f"{self.name} ({self.get_device_type_display()})"
        
    class Meta:
        verbose_name = "Dispositivo Físico"
        verbose_name_plural = "Dispositivos Físicos"


class ClientPayment(models.Model):
    """
    Historical record of payments made by a client.
    Simple ledger for display in the portal.
    """
    STATUS_CHOICES = [
        ('PENDING', _('Pendiente')),
        ('PAID', _('Pagado')),
        ('FAILED', _('Fallido')),
        ('REFUNDED', _('Reembolsado')),
    ]

    client = models.ForeignKey('clients.Client', on_delete=models.CASCADE, related_name='payments')
    
    amount = models.DecimalField(max_digits=10, decimal_places=2)
    currency = models.CharField(max_length=3, default='EUR')
    
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='PENDING')
    date = models.DateTimeField(auto_now_add=True)
    
    concept = models.CharField(max_length=255, help_text=_("Ej: Cuota Enero 2026"))
    
    # Snapshot of payment details
    payment_method = models.CharField(max_length=50, blank=True, help_text=_("Ej: Visa **** 4242"))
    stripe_payment_intent_id = models.CharField(max_length=100, blank=True)
    invoice_number = models.CharField(max_length=50, blank=True)

    class Meta:
        verbose_name = _("Pago de Cliente")
        verbose_name_plural = _("Pagos de Clientes")
        ordering = ['-date']

    def __str__(self):
        return f"{self.date.strftime('%Y-%m-%d')} - {self.client} - {self.amount}€ ({self.status})"


class Supplier(models.Model):
    """
    Proveedores del gimnasio (para gestión de gastos).
    """
    gym = models.ForeignKey(Gym, on_delete=models.CASCADE, related_name='suppliers')
    name = models.CharField(_("Nombre"), max_length=200)
    tax_id = models.CharField(_("CIF/NIF"), max_length=20, blank=True)
    email = models.EmailField(_("Email"), blank=True)
    phone = models.CharField(_("Teléfono"), max_length=20, blank=True)
    address = models.TextField(_("Dirección"), blank=True)
    
    # Banking info
    bank_account = models.CharField(_("Cuenta Bancaria (IBAN)"), max_length=34, blank=True)
    
    # Contact person
    contact_person = models.CharField(_("Persona de Contacto"), max_length=100, blank=True)
    
    notes = models.TextField(_("Notas"), blank=True)
    is_active = models.BooleanField(_("Activo"), default=True)
    
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    class Meta:
        verbose_name = _("Proveedor")
        verbose_name_plural = _("Proveedores")
        ordering = ['name']
    
    def __str__(self):
        return self.name


class ExpenseCategory(models.Model):
    """
    Categorías de gastos personalizables por gimnasio.
    """
    gym = models.ForeignKey(Gym, on_delete=models.CASCADE, related_name='expense_categories')
    name = models.CharField(_("Nombre"), max_length=100)
    color = models.CharField(_("Color"), max_length=7, default='#6366f1', help_text=_("Código hexadecimal, ej: #3b82f6"))
    icon = models.CharField(_("Icono"), max_length=50, default='💰', help_text=_("Emoji o nombre de icono"))
    description = models.TextField(_("Descripción"), blank=True)
    is_active = models.BooleanField(_("Activa"), default=True)
    
    created_at = models.DateTimeField(auto_now_add=True)
    
    class Meta:
        verbose_name = _("Categoría de Gasto")
        verbose_name_plural = _("Categorías de Gastos")
        ordering = ['name']
    
    def __str__(self):
        return f"{self.icon} {self.name}"


class Expense(models.Model):
    """
    Registro de gastos del gimnasio (puntuales y recurrentes).
    """
    STATUS_CHOICES = [
        ('PENDING', _('Pendiente de Pago')),
        ('PAID', _('Pagado')),
        ('OVERDUE', _('Vencido')),
        ('PARTIAL', _('Parcialmente Pagado')),
    ]
    
    RECURRENCE_CHOICES = [
        ('NONE', _('Puntual')),
        ('MONTHLY', _('Mensual')),
        ('QUARTERLY', _('Trimestral')),
        ('YEARLY', _('Anual')),
    ]
    
    gym = models.ForeignKey(Gym, on_delete=models.CASCADE, related_name='expenses')
    supplier = models.ForeignKey(Supplier, on_delete=models.PROTECT, related_name='expenses')
    category = models.ForeignKey(ExpenseCategory, on_delete=models.PROTECT, related_name='expenses')
    
    # Basic info
    concept = models.CharField(_("Concepto"), max_length=255)
    reference_number = models.CharField(_("Nº Factura/Referencia"), max_length=100, blank=True)
    description = models.TextField(_("Descripción"), blank=True)
    
    # Financial
    base_amount = models.DecimalField(_("Base Imponible"), max_digits=10, decimal_places=2)
    tax_rate = models.DecimalField(_("% IVA"), max_digits=5, decimal_places=2, default=21.00)
    tax_amount = models.DecimalField(_("Importe IVA"), max_digits=10, decimal_places=2, default=0.00)
    total_amount = models.DecimalField(_("Total"), max_digits=10, decimal_places=2)
    
    # Dates
    issue_date = models.DateField(_("Fecha Emisión"), help_text=_("Fecha de la factura"))
    due_date = models.DateField(_("Fecha Vencimiento"), help_text=_("Fecha límite de pago"))
    payment_date = models.DateField(_("Fecha de Pago"), null=True, blank=True)
    
    # Payment
    status = models.CharField(_("Estado"), max_length=20, choices=STATUS_CHOICES, default='PENDING')
    payment_method = models.ForeignKey(PaymentMethod, on_delete=models.SET_NULL, null=True, blank=True, related_name='expenses')
    paid_amount = models.DecimalField(_("Importe Pagado"), max_digits=10, decimal_places=2, default=0.00)
    
    # Recurrence
    is_recurring = models.BooleanField(_("Gasto Recurrente"), default=False)
    recurrence_frequency = models.CharField(_("Frecuencia"), max_length=20, choices=RECURRENCE_CHOICES, default='NONE')
    recurrence_day = models.IntegerField(_("Día del Mes"), null=True, blank=True, help_text=_("Día en que se genera (1-28)"))
    next_generation_date = models.DateField(_("Próxima Generación"), null=True, blank=True)
    parent_expense = models.ForeignKey('self', on_delete=models.SET_NULL, null=True, blank=True, related_name='generated_expenses', 
                                       help_text=_("Si este gasto fue generado automáticamente"))
    is_active_recurrence = models.BooleanField(_("Recurrencia Activa"), default=True, help_text=_("Pausar/reactivar generación automática"))
    
    # Documentation
    attachment = models.FileField(_("Adjunto (Factura)"), upload_to='expenses/%Y/%m/', null=True, blank=True)
    
    # Related to products (optional)
    related_products = models.ManyToManyField('products.Product', blank=True, related_name='expenses', 
                                              help_text=_("Productos comprados en este gasto"))
    
    notes = models.TextField(_("Notas"), blank=True)
    
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    created_by = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.SET_NULL, null=True, related_name='created_expenses')
    
    class Meta:
        verbose_name = _("Gasto")
        verbose_name_plural = _("Gastos")
        ordering = ['-due_date', '-created_at']
    
    def __str__(self):
        return f"{self.concept} - {self.total_amount}€ ({self.get_status_display()})"
    
    def save(self, *args, **kwargs):
        # Auto-calculate tax and total
        self.tax_amount = self.base_amount * (self.tax_rate / 100)
        self.total_amount = self.base_amount + self.tax_amount
        
        # Auto-update status based on dates and payment
        if self.payment_date and self.paid_amount >= self.total_amount:
            self.status = 'PAID'
        elif self.paid_amount > 0 and self.paid_amount < self.total_amount:
            self.status = 'PARTIAL'
        elif self.due_date and self.due_date < timezone.now().date() and self.status == 'PENDING':
            self.status = 'OVERDUE'
        
        super().save(*args, **kwargs)
    
    def mark_as_paid(self, payment_date=None, payment_method=None):
        """Helper method to mark expense as paid"""
        from django.utils import timezone
        self.status = 'PAID'
        self.payment_date = payment_date or timezone.now().date()
        self.paid_amount = self.total_amount
        if payment_method:
            self.payment_method = payment_method
        self.save()
    
    def generate_next_occurrence(self):
        """Generate next expense for recurring expenses"""
        if not self.is_recurring or not self.is_active_recurrence:
            return None
        
        from dateutil.relativedelta import relativedelta
        from django.utils import timezone
        
        # Calculate next date
        if self.recurrence_frequency == 'MONTHLY':
            delta = relativedelta(months=1)
        elif self.recurrence_frequency == 'QUARTERLY':
            delta = relativedelta(months=3)
        elif self.recurrence_frequency == 'YEARLY':
            delta = relativedelta(years=1)
        else:
            return None
        
        next_issue = self.issue_date + delta
        next_due = self.due_date + delta
        
        # Create new expense
        new_expense = Expense.objects.create(
            gym=self.gym,
            supplier=self.supplier,
            category=self.category,
            concept=self.concept,
            reference_number=f"{self.reference_number}-AUTO",
            description=self.description,
            base_amount=self.base_amount,
            tax_rate=self.tax_rate,
            issue_date=next_issue,
            due_date=next_due,
            is_recurring=False,  # Generated expenses are not recurring themselves
            parent_expense=self,
            created_by=self.created_by,
        )
        
        # Update next generation date
        self.next_generation_date = next_due
        self.save()
        
        return new_expense
