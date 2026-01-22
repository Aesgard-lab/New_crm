"""
API Views for Client Notifications (Mobile App).
Get popup notes and alerts.
"""
from rest_framework import views, status
from rest_framework.response import Response
from rest_framework.permissions import IsAuthenticated

from clients.models import Client, ClientNote


class PopupNotificationsView(views.APIView):
    """
    Get active popup notifications for the client.
    These are ClientNotes marked as is_popup=True.
    
    GET /api/notifications/popup/
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
        
        # Get active popup notes (WARNING or DANGER usually, but any type if is_popup=True)
        popups = ClientNote.objects.filter(
            client=client,
            is_popup=True
        ).order_by('-created_at')
        
        data = [{
            'id': note.id,
            'type': note.type, # NORMAL, VIP, WARNING, DANGER
            'text': note.text,
            'created_at': note.created_at.isoformat(),
            'author': note.author.get_full_name() if note.author else 'Sistema'
        } for note in popups]
        
        return Response({
            'popups': data
        })


class DismissPopupView(views.APIView):
    """
    Dismiss a popup (mark is_popup=False).
    
    POST /api/notifications/popup/<id>/dismiss/
    """
    permission_classes = [IsAuthenticated]
    
    def post(self, request, note_id):
        try:
            client = Client.objects.get(user=request.user)
            note = ClientNote.objects.get(id=note_id, client=client)
            
            # Disable popup flag
            note.is_popup = False
            note.save()
            
            return Response({'success': True})
            
        except (Client.DoesNotExist, ClientNote.DoesNotExist):
            return Response(
                {'error': 'Nota no encontrada'},
                status=status.HTTP_404_NOT_FOUND
            )
