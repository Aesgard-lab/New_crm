"""
API Views for Client Check-in QR (Mobile App).
Generates dynamic QR tokens for gym access.
"""
from rest_framework import views, status
from rest_framework.response import Response
from rest_framework.permissions import IsAuthenticated
import hashlib
import time

from clients.models import Client, ClientVisit


class GenerateQRTokenView(views.APIView):
    """
    Generate a QR token for check-in.
    The token refreshes every 30 seconds for security.
    
    GET or POST /api/checkin/generate/
    """
    permission_classes = [IsAuthenticated]
    
    def _generate_qr_response(self, request):
        """Shared logic for GET and POST"""
        # Get client
        try:
            client = Client.objects.get(user=request.user)
        except Client.DoesNotExist:
            return Response(
                {'error': 'Usuario no es un cliente'},
                status=status.HTTP_403_FORBIDDEN
            )
        
        # Check if client has active membership
        active_membership = client.memberships.filter(status='ACTIVE').first()
        
        # Generate QR token (refreshes every 30 seconds)
        timestamp = int(time.time() / 30)
        qr_token = hashlib.sha256(
            f"{client.id}-{client.access_code}-{timestamp}".encode()
        ).hexdigest()[:8].upper()
        
        # Calculate time until token expires
        current_time = time.time()
        next_refresh = (timestamp + 1) * 30
        expires_in = int(next_refresh - current_time)
        
        # Build membership info
        membership_info = None
        if active_membership:
            plan = active_membership.plan
            membership_info = {
                'name': plan.name if plan else 'Membresía Activa',
                'status': active_membership.status,
                'end_date': active_membership.end_date.isoformat() if active_membership.end_date else None,
                'is_unlimited': plan.duration_type == 'UNLIMITED' if plan else False,
                'sessions_remaining': active_membership.sessions_remaining if hasattr(active_membership, 'sessions_remaining') else None,
                'sessions_total': plan.sessions_included if plan and hasattr(plan, 'sessions_included') else None,
            }
        
        return Response({
            'token': qr_token,
            'expires_in': expires_in,
            'membership': membership_info
        })
    
    def get(self, request):
        """GET method for browser compatibility"""
        return self._generate_qr_response(request)
    
    def post(self, request):
        """POST method (preferred)"""
        return self._generate_qr_response(request)


class RefreshQRTokenView(views.APIView):
    """
    Refresh the QR token.
    Called by the mobile app every 30 seconds.
    
    POST /api/checkin/refresh/
    """
    permission_classes = [IsAuthenticated]
    
    def post(self, request):
        try:
            client = Client.objects.get(user=request.user)
        except Client.DoesNotExist:
            return Response(
                {'error': 'Usuario no es un cliente'},
                status=status.HTTP_403_FORBIDDEN
            )
        
        # Generate new token
        timestamp = int(time.time() / 30)
        qr_token = hashlib.sha256(
            f"{client.id}-{client.access_code}-{timestamp}".encode()
        ).hexdigest()[:8].upper()
        
        # Calculate time until token expires
        current_time = time.time()
        next_refresh = (timestamp + 1) * 30
        expires_in = int(next_refresh - current_time)
        
        return Response({
            'token': qr_token,
            'expires_in': expires_in,
            'timestamp': timestamp,
        })


class CheckinHistoryView(views.APIView):
    """
    Get client's check-in history.
    
    GET /api/checkin/history/
    Query params:
    - limit: Number of records (default 10)
    """
    permission_classes = [IsAuthenticated]
    
    def get(self, request):
        try:
            client = Client.objects.get(user=request.user)
        except Client.DoesNotExist:
            return Response(
                {'error': 'Usuario no es un cliente'},
                status=status.HTTP_403_FORBIDDEN
            )
        
        limit = int(request.query_params.get('limit', 10))
        
        visits = ClientVisit.objects.filter(
            client=client,
            status='ATTENDED'
        ).order_by('-date', '-check_in_time')[:limit]
        
        visits_data = []
        for visit in visits:
            visits_data.append({
                'id': visit.id,
                'date': visit.date.isoformat(),
                'check_in_time': visit.check_in_time.strftime('%H:%M') if visit.check_in_time else None,
                'check_out_time': visit.check_out_time.strftime('%H:%M') if visit.check_out_time else None,
                'activity': visit.activity.name if hasattr(visit, 'activity') and visit.activity else None,
            })
        
        return Response({
            'count': len(visits_data),
            'visits': visits_data,
        })
