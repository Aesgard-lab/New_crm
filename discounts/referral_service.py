"""
Servicio de Referidos
---------------------
Lógica de negocio para el sistema de referidos.
"""

import secrets
import string
from decimal import Decimal
from django.utils import timezone
from django.db import transaction
from django.conf import settings

from .models import ReferralProgram, Referral


def generate_referral_code(length=8):
    """Genera un código de referido único y legible"""
    # Caracteres que no se confunden fácilmente (sin 0, O, I, l, 1)
    alphabet = 'ABCDEFGHJKMNPQRSTUVWXYZ23456789'
    return ''.join(secrets.choice(alphabet) for _ in range(length))


def get_or_create_client_referral_code(client):
    """
    Obtiene o crea el código de referido único de un cliente.
    """
    if client.referral_code:
        return client.referral_code
    
    # Generar código único
    max_attempts = 10
    for _ in range(max_attempts):
        code = generate_referral_code()
        # Verificar que no exista
        from clients.models import Client
        if not Client.objects.filter(referral_code=code).exists():
            client.referral_code = code
            client.save(update_fields=['referral_code'])
            return code
    
    # Fallback: usar ID del cliente
    code = f"REF{client.id:06d}"
    client.referral_code = code
    client.save(update_fields=['referral_code'])
    return code


def get_active_referral_program(gym):
    """
    Obtiene el programa de referidos activo para un gimnasio.
    """
    try:
        program = ReferralProgram.objects.filter(
            gym=gym,
            is_active=True
        ).first()
        
        if program and program.is_valid():
            return program
        return None
    except ReferralProgram.DoesNotExist:
        return None


def get_referral_stats(client):
    """
    Obtiene estadísticas de referidos de un cliente.
    """
    referrals = Referral.objects.filter(referrer=client)
    
    stats = {
        'total_invited': referrals.count(),
        'pending': referrals.filter(status=Referral.Status.PENDING).count(),
        'registered': referrals.filter(status=Referral.Status.REGISTERED).count(),
        'completed': referrals.filter(status__in=[Referral.Status.COMPLETED, Referral.Status.REWARDED]).count(),
        'total_credit_earned': client.referral_credit or Decimal('0.00'),
    }
    
    return stats


def get_referral_history(client, limit=20):
    """
    Obtiene el historial de referidos de un cliente.
    """
    return Referral.objects.filter(
        referrer=client
    ).select_related('referred', 'program').order_by('-created_at')[:limit]


def validate_referral_code(code, gym):
    """
    Valida un código de referido y retorna el cliente referidor.
    """
    from clients.models import Client
    
    if not code:
        return None, "Código vacío"
    
    code = code.upper().strip()
    
    try:
        referrer = Client.objects.get(
            referral_code=code,
            gym=gym,
            status__in=['ACTIVE', 'LEAD']
        )
        
        # Verificar que hay un programa activo
        program = get_active_referral_program(gym)
        if not program:
            return None, "No hay programa de referidos activo"
        
        # Verificar límite de referidos por cliente
        if program.max_referrals_per_client > 0:
            current_referrals = Referral.objects.filter(
                referrer=referrer,
                program=program
            ).count()
            if current_referrals >= program.max_referrals_per_client:
                return None, "El cliente ha alcanzado el límite de referidos"
        
        return referrer, None
        
    except Client.DoesNotExist:
        return None, "Código de referido no válido"


@transaction.atomic
def process_referral_registration(referred_client, referral_code):
    """
    Procesa el registro de un nuevo cliente que usó un código de referido.
    """
    from clients.models import Client
    
    if not referral_code:
        return None, "No se proporcionó código de referido"
    
    gym = referred_client.gym
    
    # Validar código
    referrer, error = validate_referral_code(referral_code, gym)
    if error:
        return None, error
    
    # No puede referirse a sí mismo
    if referrer.id == referred_client.id:
        return None, "No puedes usar tu propio código"
    
    # Verificar que no haya sido referido antes
    if referred_client.referred_by:
        return None, "Este cliente ya fue referido anteriormente"
    
    # Obtener programa activo
    program = get_active_referral_program(gym)
    if not program:
        return None, "No hay programa de referidos activo"
    
    # Buscar si ya existe un referral pendiente con este email
    existing_referral = Referral.objects.filter(
        referrer=referrer,
        referred_email=referred_client.email,
        status=Referral.Status.PENDING
    ).first()
    
    if existing_referral:
        # Actualizar el referral existente
        existing_referral.mark_registered(referred_client)
        referral = existing_referral
    else:
        # Crear nuevo registro de referido
        referral = Referral.objects.create(
            program=program,
            referrer=referrer,
            referred=referred_client,
            referral_code=referrer.referral_code,
            status=Referral.Status.REGISTERED,
            registered_at=timezone.now()
        )
    
    # Marcar en el cliente quién lo refirió
    referred_client.referred_by = referrer
    referred_client.save(update_fields=['referred_by'])
    
    # Si no requiere compra de membresía, completar y dar recompensas
    if not program.require_membership_purchase:
        complete_referral_and_give_rewards(referral)
    
    # Incrementar contador del programa
    program.current_total_referrals += 1
    program.save(update_fields=['current_total_referrals'])
    
    return referral, None


@transaction.atomic
def complete_referral_and_give_rewards(referral):
    """
    Completa un referido y otorga las recompensas a ambas partes.
    """
    if referral.status == Referral.Status.REWARDED:
        return  # Ya fue procesado
    
    program = referral.program
    referrer = referral.referrer
    referred = referral.referred
    
    # Marcar como completado
    referral.mark_completed()
    
    # Dar recompensas al referidor
    if program.referrer_credit_amount > 0 and not referral.referrer_reward_given:
        referrer.referral_credit = (referrer.referral_credit or Decimal('0')) + program.referrer_credit_amount
        referrer.save(update_fields=['referral_credit'])
        referral.referrer_credit_given = program.referrer_credit_amount
    
    # TODO: Si hay descuento, crear un código personal para el referidor
    # TODO: Si hay días gratis, extender membresía
    
    # Dar recompensas al referido
    if referred and program.referred_credit_amount > 0 and not referral.referred_reward_given:
        referred.referral_credit = (referred.referral_credit or Decimal('0')) + program.referred_credit_amount
        referred.save(update_fields=['referral_credit'])
        referral.referred_credit_given = program.referred_credit_amount
    
    # Marcar recompensas dadas
    referral.mark_rewarded()
    
    # Verificar bonus por múltiples referidos
    check_and_give_bonus(referrer, program)
    
    return referral


def check_and_give_bonus(referrer, program):
    """
    Verifica si el cliente ha alcanzado el mínimo de referidos para bonus.
    """
    if program.min_referrals_for_bonus <= 0:
        return
    
    completed_referrals = Referral.objects.filter(
        referrer=referrer,
        program=program,
        status=Referral.Status.REWARDED
    ).count()
    
    # Verificar si justo alcanzó el mínimo
    if completed_referrals == program.min_referrals_for_bonus:
        # Dar bonus
        if program.bonus_credit_amount > 0:
            referrer.referral_credit = (referrer.referral_credit or Decimal('0')) + program.bonus_credit_amount
            referrer.save(update_fields=['referral_credit'])
        
        # TODO: Aplicar bonus_discount si existe


def get_referral_link(client, request=None):
    """
    Genera el link de referido para compartir.
    """
    code = get_or_create_client_referral_code(client)
    gym = client.gym
    
    # Obtener el slug del portal público
    try:
        from organizations.models import PublicPortalSettings
        settings_obj = PublicPortalSettings.objects.get(gym=gym)
        slug = settings_obj.public_slug
    except:
        slug = gym.slug
    
    # Construir URL
    if request:
        base_url = request.build_absolute_uri('/')[:-1]
    else:
        base_url = getattr(settings, 'SITE_URL', 'http://localhost:8000')
    
    return f"{base_url}/public/gym/{slug}/register/?ref={code}"


def get_share_data(client, request=None):
    """
    Obtiene los datos necesarios para compartir el código de referido.
    """
    code = get_or_create_client_referral_code(client)
    link = get_referral_link(client, request)
    gym = client.gym
    
    # Mensaje para compartir
    try:
        from organizations.models import PublicPortalSettings
        settings_obj = PublicPortalSettings.objects.get(gym=gym)
        share_message = settings_obj.referral_share_message or ""
    except:
        share_message = "¡Únete a mi gimnasio!"
    
    # Programa activo
    program = get_active_referral_program(gym)
    
    return {
        'code': code,
        'link': link,
        'share_message': share_message,
        'gym_name': gym.commercial_name or gym.name,
        'program': {
            'name': program.name if program else None,
            'referrer_reward': program.get_referrer_reward_display() if program else None,
            'referred_reward': program.get_referred_reward_display() if program else None,
        } if program else None
    }


def is_referral_enabled(gym):
    """
    Verifica si el programa de referidos está habilitado para un gimnasio.
    """
    try:
        from organizations.models import PublicPortalSettings
        settings_obj = PublicPortalSettings.objects.get(gym=gym)
        if not settings_obj.referral_program_enabled:
            return False
        
        # También verificar que hay un programa activo
        program = get_active_referral_program(gym)
        return program is not None
        
    except PublicPortalSettings.DoesNotExist:
        return False
