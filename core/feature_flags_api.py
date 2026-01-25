"""
Feature Flags API Views
"""
from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework.permissions import IsAuthenticated, IsAdminUser
from rest_framework import status

from .feature_flags import FeatureFlag, FeatureFlagService


class FeatureFlagsListView(APIView):
    """
    GET /api/feature-flags/
    
    Obtiene los feature flags activos para el usuario actual.
    """
    permission_classes = [IsAuthenticated]
    
    def get(self, request):
        enabled_flags = FeatureFlagService.get_enabled_flags_for_user(request.user)
        
        return Response({
            'flags': enabled_flags,
            'count': len(enabled_flags)
        })


class FeatureFlagCheckView(APIView):
    """
    GET /api/feature-flags/<flag_name>/
    
    Verifica si un flag especifico esta activo.
    """
    permission_classes = [IsAuthenticated]
    
    def get(self, request, flag_name):
        is_enabled = FeatureFlagService.is_enabled(flag_name, request.user)
        
        return Response({
            'name': flag_name,
            'enabled': is_enabled
        })


class FeatureFlagsAdminView(APIView):
    """
    GET/POST /api/admin/feature-flags/
    
    Administracion de feature flags (solo admin).
    """
    permission_classes = [IsAdminUser]
    
    def get(self, request):
        """Lista todos los feature flags con detalles."""
        flags = FeatureFlag.objects.all()
        
        data = []
        for flag in flags:
            data.append({
                'id': flag.id,
                'name': flag.name,
                'description': flag.description,
                'enabled': flag.enabled,
                'rollout_strategy': flag.rollout_strategy,
                'rollout_percentage': flag.rollout_percentage,
                'user_ids': flag.user_ids,
                'group_names': flag.group_names,
                'enable_at': flag.enable_at.isoformat() if flag.enable_at else None,
                'disable_at': flag.disable_at.isoformat() if flag.disable_at else None,
                'created_at': flag.created_at.isoformat(),
                'updated_at': flag.updated_at.isoformat(),
            })
        
        return Response({'flags': data})
    
    def post(self, request):
        """Crea un nuevo feature flag."""
        data = request.data
        
        try:
            flag = FeatureFlag.objects.create(
                name=data['name'],
                description=data.get('description', ''),
                enabled=data.get('enabled', False),
                rollout_strategy=data.get('rollout_strategy', 'none'),
                rollout_percentage=data.get('rollout_percentage', 0),
                user_ids=data.get('user_ids', []),
                group_names=data.get('group_names', []),
                created_by=request.user
            )
            
            return Response({
                'id': flag.id,
                'name': flag.name,
                'enabled': flag.enabled
            }, status=status.HTTP_201_CREATED)
        
        except Exception as e:
            return Response(
                {'error': str(e)},
                status=status.HTTP_400_BAD_REQUEST
            )


class FeatureFlagToggleView(APIView):
    """
    POST /api/admin/feature-flags/<flag_name>/toggle/
    
    Activa/desactiva un feature flag.
    """
    permission_classes = [IsAdminUser]
    
    def post(self, request, flag_name):
        try:
            flag = FeatureFlag.objects.get(name=flag_name)
            flag.enabled = not flag.enabled
            flag.save()
            
            return Response({
                'name': flag.name,
                'enabled': flag.enabled
            })
        
        except FeatureFlag.DoesNotExist:
            return Response(
                {'error': f"Feature flag '{flag_name}' not found"},
                status=status.HTTP_404_NOT_FOUND
            )
