"""
Quick Client Creation API
Allows creating basic client profiles from the class schedule modal.
"""
import json
from django.db.models import Q
from django.http import JsonResponse
from django.contrib.auth.decorators import login_required
from django.views.decorators.http import require_POST
from clients.models import Client


@login_required
@require_POST
def create_quick_client(request):
    """
    Create a quick client with minimal information.
    Requires: first_name, last_name, and at least one of (email, phone_number)
    Returns the client data in the same format as session search.
    """
    gym = request.gym
    
    try:
        data = json.loads(request.body)
    except json.JSONDecodeError:
        return JsonResponse({'error': 'JSON inválido'}, status=400)
    
    # Extract data
    first_name = data.get('first_name', '').strip()
    last_name = data.get('last_name', '').strip()
    email = data.get('email', '').strip()
    phone_number = data.get('phone_number', '').strip()
    
    # Validate required fields
    if not first_name:
        return JsonResponse({'error': 'El nombre es obligatorio'}, status=400)
    
    if not last_name:
        return JsonResponse({'error': 'Los apellidos son obligatorios'}, status=400)
    
    # At least one contact method required
    if not email and not phone_number:
        return JsonResponse({'error': 'Debes proporcionar al menos un email o teléfono'}, status=400)
    
    # Check for duplicates
    duplicate_check = Q(gym=gym)
    if email:
        duplicate_check &= Q(email__iexact=email)
    if phone_number:
        duplicate_check |= Q(phone_number=phone_number, gym=gym)
    
    existing_client = Client.objects.filter(duplicate_check).first()
    if existing_client:
        return JsonResponse({
            'error': f'Ya existe un cliente con estos datos: {existing_client.first_name} {existing_client.last_name}',
            'existing_client_id': existing_client.id
        }, status=409)  # 409 Conflict
    
    # Create the client
    client = Client.objects.create(
        gym=gym,
        first_name=first_name,
        last_name=last_name,
        email=email if email else '',
        phone_number=phone_number if phone_number else '',
        status=Client.Status.ACTIVE  # New clients from class booking are active
    )
    
    # Return in the same format as search results
    return JsonResponse({
        'status': 'ok',
        'client': {
            'id': client.id,
            'name': f"{client.first_name} {client.last_name}",
            'email': client.email,
            'phone': client.phone_number,
            'avatar': client.photo.url if client.photo else None,
        }
    })
