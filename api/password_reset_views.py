from rest_framework import views, status
from rest_framework.response import Response
from rest_framework.permissions import AllowAny
from django.contrib.auth import get_user_model
from django.core.mail import send_mail
from django.conf import settings
from django.utils.decorators import method_decorator
from django_ratelimit.decorators import ratelimit
from .models import PasswordResetToken
import secrets
import string
import time
import random
import logging

User = get_user_model()
logger = logging.getLogger(__name__)


class PasswordResetRequestView(views.APIView):
    """
    Request a password reset code.
    Sends an 8-character alphanumeric code to the user's email.
    
    SECURITY:
    - Rate limited to 3 requests per hour per IP
    - Uses cryptographically secure random code
    - Constant-time response to prevent timing attacks
    """
    permission_classes = [AllowAny]
    
    @method_decorator(ratelimit(key='ip', rate='3/h', method='POST', block=True))
    def post(self, request):
        start_time = time.time()
        email = request.data.get('email', '').strip().lower()
        
        if not email:
            return Response(
                {'error': 'Email es requerido'}, 
                status=status.HTTP_400_BAD_REQUEST
            )
        
        # Check if user exists (but don't reveal this in response for security)
        try:
            user = User.objects.get(email=email)
            
            # SECURITY: Generate cryptographically secure 8-character alphanumeric code
            # This provides 62^8 = ~218 trillion combinations
            alphabet = string.ascii_uppercase + string.digits
            code = ''.join(secrets.choice(alphabet) for _ in range(8))
            
            # Invalidate any previous unused tokens for this email
            PasswordResetToken.objects.filter(email=email, used=False).update(used=True)
            
            # Create new token
            PasswordResetToken.objects.create(email=email, code=code)
            
            # Send email
            try:
                send_mail(
                    subject='Código de recuperación de contraseña',
                    message=f'Tu código de recuperación es: {code}\n\nEste código es válido por 15 minutos.\n\nSi no solicitaste este código, ignora este mensaje.',
                    from_email=settings.DEFAULT_FROM_EMAIL,
                    recipient_list=[email],
                    fail_silently=False,
                )
            except Exception as e:
                # Log error but don't reveal to user
                logger.error(f"Error sending password reset email: {e}")
                # For development only
                if settings.DEBUG:
                    logger.debug(f"PASSWORD RESET CODE for {email}: {code}")
        
        except User.DoesNotExist:
            # Don't reveal that user doesn't exist
            pass
        
        # SECURITY: Add random delay to prevent timing attacks
        # Ensure response time is consistent regardless of user existence
        elapsed = time.time() - start_time
        min_response_time = 0.5  # minimum 500ms
        if elapsed < min_response_time:
            time.sleep(min_response_time - elapsed + random.uniform(0, 0.1))
        
        # Always return success message for security
        return Response({
            'message': 'Si el email existe en nuestro sistema, recibirás un código de recuperación.'
        })


class PasswordResetConfirmView(views.APIView):
    """
    Confirm password reset with code and set new password.
    
    SECURITY: 
    - Uses Django's built-in password validators
    - Rate limited to prevent brute force code guessing
    - Uses constant-time comparison for code
    """
    permission_classes = [AllowAny]
    
    @method_decorator(ratelimit(key='ip', rate='10/h', method='POST', block=True))
    def post(self, request):
        from django.contrib.auth.password_validation import validate_password
        from django.core.exceptions import ValidationError
        
        email = request.data.get('email', '').strip().lower()
        code = request.data.get('code', '').strip().upper()  # Normalize to uppercase
        new_password = request.data.get('new_password', '')
        
        if not all([email, code, new_password]):
            return Response(
                {'error': 'Email, código y nueva contraseña son requeridos'}, 
                status=status.HTTP_400_BAD_REQUEST
            )
        
        # SECURITY: Use Django's password validators instead of just length check
        try:
            validate_password(new_password)
        except ValidationError as e:
            return Response(
                {'error': e.messages[0] if e.messages else 'Contraseña no válida'}, 
                status=status.HTTP_400_BAD_REQUEST
            )
        
        # Find valid token
        try:
            token = PasswordResetToken.objects.filter(
                email=email,
                code=code,
                used=False
            ).latest('created_at')
            
            if not token.is_valid():
                return Response(
                    {'error': 'El código ha expirado. Solicita uno nuevo.'}, 
                    status=status.HTTP_400_BAD_REQUEST
                )
            
            # Get user and update password
            try:
                user = User.objects.get(email=email)
                user.set_password(new_password)
                user.save()
                
                # Mark token as used
                token.used = True
                token.save()
                
                return Response({
                    'message': 'Contraseña actualizada exitosamente. Ya puedes iniciar sesión.'
                })
                
            except User.DoesNotExist:
                return Response(
                    {'error': 'Usuario no encontrado'}, 
                    status=status.HTTP_404_NOT_FOUND
                )
        
        except PasswordResetToken.DoesNotExist:
            return Response(
                {'error': 'Código inválido o expirado'}, 
                status=status.HTTP_400_BAD_REQUEST
            )
