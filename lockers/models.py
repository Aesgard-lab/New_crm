"""
Módulo de Taquillas
===================
Gestión de taquillas/lockers para clientes del gimnasio.

Modelos:
- LockerZone: Zonas de taquillas (vestuario hombres, mujeres, etc.)
- Locker: Taquilla individual
- LockerAssignment: Asignación de taquilla a cliente
"""

from django.db import models
from django.utils.translation import gettext_lazy as _
from django.utils import timezone
from decimal import Decimal


class LockerZone(models.Model):
    """
    Zona de taquillas (ej: Vestuario Hombres, Vestuario Mujeres, etc.)
    """
    gym = models.ForeignKey('organizations.Gym', on_delete=models.CASCADE, related_name='locker_zones')
    name = models.CharField(_("Nombre de la zona"), max_length=100)
    description = models.TextField(_("Descripción"), blank=True)
    color = models.CharField(_("Color"), max_length=7, default="#6366F1", help_text="Código HEX")
    
    # Configuración de la zona
    rows = models.PositiveIntegerField(_("Filas"), default=4, help_text="Número de filas de taquillas")
    columns = models.PositiveIntegerField(_("Columnas"), default=10, help_text="Número de columnas de taquillas")
    
    is_active = models.BooleanField(_("Activa"), default=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    class Meta:
        verbose_name = _("Zona de Taquillas")
        verbose_name_plural = _("Zonas de Taquillas")
        ordering = ['name']
    
    def __str__(self):
        return f"{self.name} ({self.gym.name})"
    
    @property
    def total_lockers(self):
        return self.lockers.count()
    
    @property
    def available_lockers(self):
        return self.lockers.filter(status='AVAILABLE').count()
    
    @property
    def assigned_lockers(self):
        return self.lockers.filter(status='ASSIGNED').count()


class Locker(models.Model):
    """
    Taquilla individual.
    """
    STATUS_CHOICES = [
        ('AVAILABLE', _("Disponible")),
        ('ASSIGNED', _("Asignada")),
        ('MAINTENANCE', _("En mantenimiento")),
        ('RESERVED', _("Reservada")),
    ]
    
    SIZE_CHOICES = [
        ('S', _("Pequeña")),
        ('M', _("Mediana")),
        ('L', _("Grande")),
        ('XL', _("Extra Grande")),
    ]
    
    zone = models.ForeignKey(LockerZone, on_delete=models.CASCADE, related_name='lockers')
    number = models.CharField(_("Número"), max_length=20)
    
    # Posición en la cuadrícula (opcional, para visualización)
    row = models.PositiveIntegerField(_("Fila"), null=True, blank=True)
    column = models.PositiveIntegerField(_("Columna"), null=True, blank=True)
    
    # Características
    size = models.CharField(_("Tamaño"), max_length=2, choices=SIZE_CHOICES, default='M')
    has_key = models.BooleanField(_("Tiene llave"), default=True)
    key_number = models.CharField(_("Número de llave"), max_length=50, blank=True)
    has_lock = models.BooleanField(_("Tiene candado"), default=False)
    lock_combination = models.CharField(_("Combinación"), max_length=50, blank=True)
    
    # Precio mensual por defecto
    monthly_price = models.DecimalField(
        _("Precio mensual"),
        max_digits=8,
        decimal_places=2,
        default=Decimal('0.00'),
        help_text=_("0 = gratuita")
    )
    
    status = models.CharField(_("Estado"), max_length=20, choices=STATUS_CHOICES, default='AVAILABLE')
    notes = models.TextField(_("Notas"), blank=True)
    
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    class Meta:
        verbose_name = _("Taquilla")
        verbose_name_plural = _("Taquillas")
        ordering = ['zone', 'number']
        unique_together = ['zone', 'number']
    
    def __str__(self):
        return f"Taquilla {self.number} - {self.zone.name}"
    
    @property
    def current_assignment(self):
        """Retorna la asignación activa actual, si existe."""
        return self.assignments.filter(
            status='ACTIVE',
            end_date__gte=timezone.now().date()
        ).first()
    
    @property
    def is_available(self):
        return self.status == 'AVAILABLE'


class LockerAssignment(models.Model):
    """
    Asignación de una taquilla a un cliente.
    """
    STATUS_CHOICES = [
        ('ACTIVE', _("Activa")),
        ('EXPIRED', _("Expirada")),
        ('CANCELLED', _("Cancelada")),
    ]
    
    locker = models.ForeignKey(Locker, on_delete=models.CASCADE, related_name='assignments')
    client = models.ForeignKey('clients.Client', on_delete=models.CASCADE, related_name='locker_assignments')
    
    # Período de asignación
    start_date = models.DateField(_("Fecha inicio"))
    end_date = models.DateField(_("Fecha fin"), null=True, blank=True, help_text=_("Dejar vacío para indefinido"))
    
    # Precio (puede diferir del precio por defecto de la taquilla)
    price = models.DecimalField(
        _("Precio mensual"),
        max_digits=8,
        decimal_places=2,
        default=Decimal('0.00')
    )
    is_included_in_membership = models.BooleanField(
        _("Incluida en membresía"),
        default=False,
        help_text=_("Si está marcado, no se cobra aparte")
    )
    
    # Llave/Candado
    key_delivered = models.BooleanField(_("Llave entregada"), default=False)
    key_delivered_date = models.DateField(_("Fecha entrega llave"), null=True, blank=True)
    key_returned = models.BooleanField(_("Llave devuelta"), default=False)
    key_returned_date = models.DateField(_("Fecha devolución llave"), null=True, blank=True)
    
    # Depósito
    deposit_amount = models.DecimalField(
        _("Depósito"),
        max_digits=8,
        decimal_places=2,
        default=Decimal('0.00')
    )
    deposit_paid = models.BooleanField(_("Depósito pagado"), default=False)
    deposit_returned = models.BooleanField(_("Depósito devuelto"), default=False)
    
    status = models.CharField(_("Estado"), max_length=20, choices=STATUS_CHOICES, default='ACTIVE')
    notes = models.TextField(_("Notas"), blank=True)
    
    # Tracking
    assigned_by = models.ForeignKey(
        'accounts.User',
        on_delete=models.SET_NULL,
        null=True,
        related_name='locker_assignments_made'
    )
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    class Meta:
        verbose_name = _("Asignación de Taquilla")
        verbose_name_plural = _("Asignaciones de Taquillas")
        ordering = ['-created_at']
    
    def __str__(self):
        return f"{self.locker.number} → {self.client} ({self.get_status_display()})"
    
    def save(self, *args, **kwargs):
        # Actualizar estado de la taquilla
        if self.status == 'ACTIVE':
            self.locker.status = 'ASSIGNED'
            self.locker.save()
        elif self.status in ['EXPIRED', 'CANCELLED']:
            # Verificar si hay otras asignaciones activas
            other_active = self.locker.assignments.filter(status='ACTIVE').exclude(pk=self.pk).exists()
            if not other_active:
                self.locker.status = 'AVAILABLE'
                self.locker.save()
        super().save(*args, **kwargs)
    
    @property
    def is_active(self):
        if self.status != 'ACTIVE':
            return False
        today = timezone.now().date()
        if self.end_date and self.end_date < today:
            return False
        return True
    
    @property
    def days_remaining(self):
        if not self.end_date:
            return None  # Indefinido
        today = timezone.now().date()
        delta = self.end_date - today
        return max(0, delta.days)
