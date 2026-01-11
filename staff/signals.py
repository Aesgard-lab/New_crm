from django.db.models.signals import post_save
from django.dispatch import receiver
from clients.models import ClientSale
from .models import StaffCommission, IncentiveRule

@receiver(post_save, sender=ClientSale)
def calculate_sale_commission(sender, instance, created, **kwargs):
    """
    Calcula automáticamente la comisión cuando se crea una venta.
    """
    if not created or not instance.staff:
        # Solo calculamos al crear y si hay vendedor asignado
        return

    seller = instance.staff
    sale_amount = instance.amount
    gym = seller.gym

    # 1. Buscar reglas aplicables
    # Prioridad: Regla específica del empleado > Regla global del gym
    
    # Buscamos todas las reglas activas que apliquen a VENTAS (PCT o FIXED)
    # Filtro 1: Reglas asignadas a este staff O reglas globales (staff=None) del mismo gym
    rules = IncentiveRule.objects.filter(
        gym=gym, 
        is_active=True,
        type__in=[IncentiveRule.Type.SALE_PCT, IncentiveRule.Type.SALE_FIXED]
    ).filter(
        # Lógica OR compleja en Django ORM: (staff=seller) OR (staff=None)
        # Lo hacemos en memoria o con Q objects. Usando Q es mejor.
    )
    
    # Re-fetch con Q objects para hacerlo bien
    from django.db.models import Q
    rules = IncentiveRule.objects.filter(
        Q(staff=seller) | Q(staff__isnull=True),
        gym=gym,
        is_active=True,
        type__in=[IncentiveRule.Type.SALE_PCT, IncentiveRule.Type.SALE_FIXED]
    )

    for rule in rules:
        # Aquí iría lógica extra de 'criteria' (ej: si la regla solo aplica a producto 'bono')
        # Por ahora asumimos que aplica a todo (MVP)
        
        commission_amount = 0
        
        if rule.type == IncentiveRule.Type.SALE_PCT:
            # Value es porcentaje (ej: 10 para 10%)
            commission_amount = (sale_amount * rule.value) / 100
        elif rule.type == IncentiveRule.Type.SALE_FIXED:
            # Value es cantidad fija
            commission_amount = rule.value
            
        if commission_amount > 0:
            StaffCommission.objects.create(
                staff=seller,
                rule=rule,
                concept=f"Comisión por venta: {instance.concept}",
                amount=commission_amount
            )

@receiver(post_save, sender="staff.StaffTask")
def pay_task_incentive(sender, instance, created, **kwargs):
    """
    Paga el incentivo cuando una tarea pasa a estado VERIFIED.
    """
    # Solo procesamos si está VERIFICADA, tiene recompensa > 0 y sabemos quién la hizo
    if instance.status == "VERIFIED" and instance.incentive_amount > 0 and instance.completed_by:
        
        # Evitar duplicar pagos: comprobamos si ya existe una comisión por esta tarea
        # Usamos el concepto como identificador único simple por ahora
        concept_str = f"Recompensa tarea: {instance.title} (#{instance.id})"
        exists = StaffCommission.objects.filter(staff=instance.completed_by, concept=concept_str).exists()
        
        if not exists:
            StaffCommission.objects.create(
                staff=instance.completed_by,
                concept=concept_str,
                amount=instance.incentive_amount,
                # No asignamos 'rule' porque esto es un pago directo por tarea, no por regla general
            )

