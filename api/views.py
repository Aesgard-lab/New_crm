from rest_framework import views, status, generics
from rest_framework.response import Response
from rest_framework.authtoken.models import Token
from rest_framework.permissions import IsAuthenticated, AllowAny
from django.contrib.auth import authenticate
from django.db.models import Q
from organizations.models import Gym
from .serializers import GymSerializer, ClientProfileSerializer


class SystemConfigView(views.APIView):
    """
    Public endpoint to get system branding (name, logo).
    For white-label login screens.
    """
    permission_classes = [AllowAny]
    
    def get(self, request):
        from saas_billing.models import BillingConfig
        
        try:
            config = BillingConfig.get_config()
            return Response({
                'system_name': config.system_name or 'Gym Portal',
                'system_logo': request.build_absolute_uri(config.system_logo.url) if config.system_logo else None,
            })
        except Exception:
            return Response({
                'system_name': 'Gym Portal',
                'system_logo': None,
            })


class GymSearchView(generics.ListAPIView):
    """
    Public endpoint to search gyms by name.
    """
    permission_classes = [AllowAny]
    serializer_class = GymSerializer
    
    def get_queryset(self):
        query = self.request.query_params.get('q', '')
        if len(query) < 2:
            return Gym.objects.none()
        
        return Gym.objects.filter(
            Q(name__icontains=query) | Q(city__icontains=query)
        )[:10]

class LoginView(views.APIView):
    """
    Login endpoint. Returns auth token and client profile.
    Optional: 'gym_id' to validate user belongs to that gym.
    """
    permission_classes = [AllowAny]

    def post(self, request):
        email = request.data.get('email')
        password = request.data.get('password')
        gym_id = request.data.get('gym_id')

        if not email or not password:
            return Response({'error': 'Email and password required'}, status=status.HTTP_400_BAD_REQUEST)

        user = authenticate(username=email, password=password)

        if not user:
            return Response({'error': 'Invalid credentials'}, status=status.HTTP_400_BAD_REQUEST)

        # Check if user has a client profile
        if not hasattr(user, 'client_profile'):
            return Response({'error': 'User is not a client'}, status=status.HTTP_403_FORBIDDEN)
        
        client = user.client_profile
        
        # Validate Gym if provided (User requested strict login to this gym)
        if gym_id:
            try:
                rq_gym_id = int(gym_id)
                if client.gym_id != rq_gym_id:
                     return Response({
                         'error': 'User does not belong to this gym',
                         'user_gym': client.gym.name 
                     }, status=status.HTTP_403_FORBIDDEN)
            except ValueError:
                pass

        token, _ = Token.objects.get_or_create(user=user)
        
        return Response({
            'token': token.key,
            'client': ClientProfileSerializer(client).data
        })

class CheckAuthView(views.APIView):
    """
    Verify token validity.
    """
    permission_classes = [IsAuthenticated]
    
    def get(self, request):
        return Response({
            'status': 'ok',
            'client': ClientProfileSerializer(request.user.client_profile).data
        })
