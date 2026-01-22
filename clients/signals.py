"""
Signals para auto-generar documentos cuando se requieran contratos
"""
from django.db.models.signals import post_save
from django.dispatch import receiver
from django.utils import timezone
from .models import ClientMembership, ClientDocument


@receiver(post_save, sender=ClientMembership)
def create_contract_document(sender, instance, created, **kwargs):
    """
    Auto-genera un documento de contrato cuando se crea una membresía
    que tiene un plan con contract_required=True
    """
    if not created:
        return
    
    # Intentar obtener el plan original desde OrderItem o similar
    # Por ahora, vamos a buscar si el nombre de la membresía corresponde a un plan
    from memberships.models import MembershipPlan
    
    # Buscar plan por nombre (puede no ser exacto)
    try:
        plan = MembershipPlan.objects.filter(
            name__icontains=instance.name,
            gym=instance.client.gym,
            contract_required=True
        ).first()
        
        if plan and plan.contract_content:
            # Verificar si ya existe un documento para esta membresía
            existing = ClientDocument.objects.filter(
                client=instance.client,
                membership_plan=plan,
                document_type='CONTRACT'
            ).exists()
            
            if not existing:
                # Crear documento
                doc = ClientDocument.objects.create(
                    client=instance.client,
                    name=f"Contrato: {plan.name}",
                    document_type='CONTRACT',
                    content=plan.contract_content,
                    requires_signature=True,
                    status='PENDING',
                    sent_at=timezone.now(),
                    membership_plan=plan
                )
                print(f"✅ Documento de contrato creado automáticamente: {doc.name}")
    except Exception as e:
        print(f"⚠️ Error al crear documento automático: {e}")
