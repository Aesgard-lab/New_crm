"""
API Views for Client Notifications (Mobile App).
Get popup notes and alerts.
"""
from rest_framework import views, status
from rest_framework.response import Response
from rest_framework.permissions import IsAuthenticated
from django.utils import timezone
from django.db.models import Q

from clients.models import Client, ClientNote
from marketing.models import Popup, PopupRead


class PopupNotificationsView(views.APIView):
    """
    Get active popup notifications for the client.
    Includes both:
    - ClientNotes marked as is_popup=True (personal alerts)
    - Marketing Popups targeted at the client (general notifications)
    
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
        
        data = []
        now = timezone.now()
        
        # 1. Get ClientNote popups (personal alerts from staff)
        client_notes = ClientNote.objects.filter(
            client=client,
            is_popup=True
        ).order_by('-created_at')
        
        for note in client_notes:
            data.append({
                'id': note.id,
                'source': 'note',
                'type': note.type,  # NORMAL, VIP, WARNING, DANGER
                'title': f'Mensaje del Staff',
                'text': note.text,
                'created_at': note.created_at.isoformat(),
                'author': note.author.get_full_name() if note.author else 'Sistema',
                'image': None
            })
        
        # 2. Get Marketing Popups (general notifications)
        # Get IDs of popups already read by this client
        read_popup_ids = PopupRead.objects.filter(
            client=client
        ).values_list('popup_id', flat=True)
        
        # Get active popups for this client's gym
        marketing_popups = Popup.objects.filter(
            gym=client.gym,
            is_active=True,
            start_date__lte=now
        ).filter(
            Q(end_date__isnull=True) | Q(end_date__gte=now)
        ).filter(
            # Target: either ALL clients, or specifically this client
            Q(target_client__isnull=True) | Q(target_client=client)
        ).exclude(
            # Exclude already read popups
            id__in=read_popup_ids
        ).order_by('-created_at')
        
        for popup in marketing_popups:
            # Map priority to type for Flutter app
            type_map = {
                'INFO': 'NORMAL',
                'WARNING': 'WARNING',
                'URGENT': 'DANGER'
            }
            data.append({
                'id': popup.id,
                'source': 'marketing',
                'type': type_map.get(popup.priority, 'NORMAL'),
                'title': popup.title,
                'text': popup.content,
                'created_at': popup.created_at.isoformat(),
                'author': 'Gimnasio',
                'image': popup.image.url if popup.image else None
            })
        
        # Return list directly (Flutter app expects List<dynamic>)
        return Response(data)


class DismissPopupView(views.APIView):
    """
    Dismiss a popup.
    
    POST /api/notifications/popup/<id>/dismiss/
    
    Tries to find and dismiss both ClientNote and Marketing Popup with the given ID.
    """
    permission_classes = [IsAuthenticated]
    
    def post(self, request, note_id):
        try:
            client = Client.objects.get(user=request.user)
        except Client.DoesNotExist:
            return Response(
                {'error': 'Usuario no es un cliente'},
                status=status.HTTP_403_FORBIDDEN
            )
        
        # Try to get source from body (optional)
        source = request.data.get('source', None)
        
        # If source specified, handle accordingly
        if source == 'marketing':
            try:
                popup = Popup.objects.get(id=note_id, gym=client.gym)
                PopupRead.objects.get_or_create(
                    popup=popup,
                    client=client
                )
                return Response({'success': True})
            except Popup.DoesNotExist:
                return Response(
                    {'error': 'Popup no encontrado'},
                    status=status.HTTP_404_NOT_FOUND
                )
        elif source == 'note':
            try:
                note = ClientNote.objects.get(id=note_id, client=client)
                note.is_popup = False
                note.save()
                return Response({'success': True})
            except ClientNote.DoesNotExist:
                return Response(
                    {'error': 'Nota no encontrada'},
                    status=status.HTTP_404_NOT_FOUND
                )
        
        # If no source specified, try both (backward compatibility)
        # First try ClientNote
        try:
            note = ClientNote.objects.get(id=note_id, client=client)
            note.is_popup = False
            note.save()
            return Response({'success': True})
        except ClientNote.DoesNotExist:
            pass
        
        # Then try Marketing Popup
        try:
            popup = Popup.objects.get(id=note_id, gym=client.gym)
            PopupRead.objects.get_or_create(
                popup=popup,
                client=client
            )
            return Response({'success': True})
        except Popup.DoesNotExist:
            pass
        
        return Response(
            {'error': 'Notificación no encontrada'},
            status=status.HTTP_404_NOT_FOUND
        )
