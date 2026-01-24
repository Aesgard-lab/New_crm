from rest_framework import views, status
from rest_framework.response import Response
from rest_framework.permissions import AllowAny
from django.contrib.auth import get_user_model
from django.core.mail import send_mail
from django.conf import settings
from .models import PasswordResetToken
import random
import string

User = get_user_model()

class PasswordResetRequestView(views.APIView):
    """
    Request a password reset code.
    Sends a 6-digit code to the user's email.
    """
    permission_classes = [AllowAny]
    
    def post(self, request):
        email = request.data.get('email', '').strip().lower()
        
        if not email:
            return Response(
                {'error': 'Email es requerido'}, 
                status=status.HTTP_400_BAD_REQUEST
            )
        
        # Check if user exists (but don't reveal this in response for security)
        try:
            user = User.objects.get(email=email)
            
            # Generate 6-digit code
            code = ''.join(random.choices(string.digits, k=6))
            
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
                print(f"Error sending email: {e}")
                # For development, print the code
                print(f"PASSWORD RESET CODE for {email}: {code}")
        
        except User.DoesNotExist:
            # Don't reveal that user doesn't exist
            pass
        
        # Always return success message for security
        return Response({
            'message': 'Si el email existe en nuestro sistema, recibirás un código de recuperación.'
        })


class PasswordResetConfirmView(views.APIView):
    """
    Confirm password reset with code and set new password.
    
    SECURITY: Uses Django's built-in password validators
    """
    permission_classes = [AllowAny]
    
    def post(self, request):
        from django.contrib.auth.password_validation import validate_password
        from django.core.exceptions import ValidationError
        
        email = request.data.get('email', '').strip().lower()
        code = request.data.get('code', '').strip()
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
