"""
Registration API endpoints for mobile apps.
Allows clients to self-register if enabled by the gym.
"""
from rest_framework import views, status
from rest_framework.response import Response
from rest_framework.permissions import AllowAny
from rest_framework.authtoken.models import Token
from django.contrib.auth import get_user_model
from django.db import transaction

from organizations.models import Gym, PublicPortalSettings
from clients.models import Client, ClientField

User = get_user_model()


class RegistrationConfigView(views.APIView):
    """
    GET /api/registration/config/?gym_id=<id>
    Returns registration configuration for a gym:
    - whether registration is enabled
    - required fields (both standard and custom)
    - franchise gyms (if applicable)
    """
    permission_classes = [AllowAny]
    
    def get(self, request):
        gym_id = request.query_params.get('gym_id')
        
        if not gym_id:
            return Response({
                'error': 'gym_id is required'
            }, status=status.HTTP_400_BAD_REQUEST)
        
        try:
            gym = Gym.objects.get(id=gym_id, is_active=True)
        except Gym.DoesNotExist:
            return Response({
                'error': 'Gym not found or inactive'
            }, status=status.HTTP_404_NOT_FOUND)
        
        # Get portal settings
        try:
            portal_settings = PublicPortalSettings.objects.get(gym=gym)
        except PublicPortalSettings.DoesNotExist:
            # No settings means registration is disabled
            return Response({
                'allow_registration': False,
                'message': 'Registration not configured for this gym'
            })
        
        if not portal_settings.allow_self_registration:
            return Response({
                'allow_registration': False,
                'message': 'Registration is currently disabled'
            })
        
        # Get custom fields configured for registration
        custom_fields = ClientField.objects.filter(
            gym=gym,
            is_active=True,
            show_in_registration=True
        ).prefetch_related('options').order_by('display_order', 'name')
        
        fields_data = []
        for field in custom_fields:
            field_data = {
                'id': field.id,
                'slug': field.slug,
                'name': field.name,
                'field_type': field.field_type,
                'is_required': field.is_required,
                'placeholder': field.placeholder or '',
            }
            
            # Add options for SELECT fields
            if field.field_type == ClientField.FieldType.SELECT:
                field_data['options'] = [
                    {'value': opt.value, 'label': opt.label}
                    for opt in field.options.all().order_by('order')
                ]
            
            fields_data.append(field_data)
        
        # Get franchise gyms if applicable
        franchise_gyms = []
        if gym.franchise:
            franchise_gyms = [
                {'id': g.id, 'name': g.name, 'city': g.city or ''}
                for g in gym.franchise.gyms.filter(is_active=True).order_by('name')
            ]
        
        return Response({
            'allow_registration': True,
            'require_email_verification': portal_settings.require_email_verification,
            'require_staff_approval': portal_settings.require_staff_approval,
            'gym': {
                'id': gym.id,
                'name': gym.name,
                'logo_url': gym.logo.url if gym.logo else None,
            },
            'standard_fields': [
                {'name': 'first_name', 'label': 'Nombre', 'required': True, 'type': 'text'},
                {'name': 'last_name', 'label': 'Apellidos', 'required': True, 'type': 'text'},
                {'name': 'email', 'label': 'Email', 'required': True, 'type': 'email'},
                {'name': 'password', 'label': 'Contraseña', 'required': True, 'type': 'password'},
                {'name': 'phone_number', 'label': 'Teléfono', 'required': False, 'type': 'phone'},
            ],
            'custom_fields': fields_data,
            'franchise_gyms': franchise_gyms,
        })


class RegisterClientView(views.APIView):
    """
    POST /api/registration/register/
    Register a new client account.
    
    Required body:
    - gym_id: ID of the gym to register with
    - first_name: Client's first name
    - last_name: Client's last name  
    - email: Client's email address
    - password: Account password
    
    Optional:
    - phone_number: Client's phone
    - custom_fields: Dict of custom field values (key: field slug, value: field value)
    """
    permission_classes = [AllowAny]
    
    @transaction.atomic
    def post(self, request):
        data = request.data
        
        # Validate required fields
        gym_id = data.get('gym_id')
        first_name = data.get('first_name', '').strip()
        last_name = data.get('last_name', '').strip()
        email = data.get('email', '').strip().lower()
        password = data.get('password', '')
        phone_number = data.get('phone_number', '').strip()
        custom_field_values = data.get('custom_fields', {})
        
        if not all([gym_id, first_name, last_name, email, password]):
            return Response({
                'error': 'Missing required fields',
                'required': ['gym_id', 'first_name', 'last_name', 'email', 'password']
            }, status=status.HTTP_400_BAD_REQUEST)
        
        # Validate gym exists and registration is enabled
        try:
            gym = Gym.objects.get(id=gym_id, is_active=True)
        except Gym.DoesNotExist:
            return Response({
                'error': 'Gym not found or inactive'
            }, status=status.HTTP_404_NOT_FOUND)
        
        try:
            portal_settings = PublicPortalSettings.objects.get(gym=gym)
        except PublicPortalSettings.DoesNotExist:
            return Response({
                'error': 'Registration not available for this gym'
            }, status=status.HTTP_403_FORBIDDEN)
        
        if not portal_settings.allow_self_registration:
            return Response({
                'error': 'Registration is currently disabled'
            }, status=status.HTTP_403_FORBIDDEN)
        
        # Check if email is already used
        if User.objects.filter(email=email).exists():
            return Response({
                'error': 'An account with this email already exists'
            }, status=status.HTTP_400_BAD_REQUEST)
        
        # Validate custom required fields
        custom_fields = ClientField.objects.filter(
            gym=gym,
            is_active=True,
            show_in_registration=True,
            is_required=True
        )
        
        missing_fields = []
        for field in custom_fields:
            if field.slug not in custom_field_values or not custom_field_values[field.slug]:
                missing_fields.append(field.name)
        
        if missing_fields:
            return Response({
                'error': 'Missing required custom fields',
                'missing_fields': missing_fields
            }, status=status.HTTP_400_BAD_REQUEST)
        
        # Create user account
        user = User.objects.create_user(
            username=email,
            email=email,
            password=password,
            first_name=first_name,
            last_name=last_name
        )
        
        # Build extra_data from custom fields
        extra_data = {}
        all_custom_fields = ClientField.objects.filter(
            gym=gym, is_active=True, show_in_registration=True
        )
        for field in all_custom_fields:
            if field.slug in custom_field_values:
                value = custom_field_values[field.slug]
                # Convert boolean strings for toggle fields
                if field.field_type == ClientField.FieldType.TOGGLE:
                    value = str(value).lower() in ('true', '1', 'yes', 'on')
                extra_data[field.slug] = value
        
        # Create client profile
        client = Client.objects.create(
            user=user,
            gym=gym,
            first_name=first_name,
            last_name=last_name,
            email=email,
            phone_number=phone_number,
            extra_data=extra_data,
            is_active=not portal_settings.require_staff_approval  # Pending approval if required
        )
        
        # Generate auth token
        token, _ = Token.objects.get_or_create(user=user)
        
        # Prepare response
        response_data = {
            'success': True,
            'message': 'Account created successfully',
            'client': {
                'id': client.id,
                'first_name': client.first_name,
                'last_name': client.last_name,
                'email': client.email,
                'gym_id': gym.id,
                'gym_name': gym.name,
            }
        }
        
        # Include token only if no approval is required
        if not portal_settings.require_staff_approval:
            response_data['token'] = token.key
        else:
            response_data['pending_approval'] = True
            response_data['message'] = 'Account created. Pending staff approval before you can log in.'
        
        # Note about email verification (handled separately)
        if portal_settings.require_email_verification:
            response_data['requires_email_verification'] = True
            # TODO: Send verification email
        
        return Response(response_data, status=status.HTTP_201_CREATED)
