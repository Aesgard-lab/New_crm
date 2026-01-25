"""
API Views for Client Chat (Mobile App).
Real-time messaging between client and gym staff.
"""
from rest_framework import views, status
from rest_framework.response import Response
from rest_framework.permissions import IsAuthenticated
from django.db.models import Q
from django.utils import timezone

from clients.models import Client, ChatRoom, ChatMessage
from accounts.models import User


class ChatRoomView(views.APIView):
    """
    Get or create chat room for the current client.
    
    GET /api/chat/room/
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
        
        # Get or create room
        room, created = ChatRoom.objects.get_or_create(
            client=client,
            defaults={'gym': client.gym}
        )
        
        return Response({
            'room_id': room.id,
            'gym_name': client.gym.name,
            'last_message_at': room.last_message_at
        })


class ChatMessagesView(views.APIView):
    """
    List and send messages.
    
    GET /api/chat/messages/?limit=50&offset=0
    POST /api/chat/messages/
    """
    permission_classes = [IsAuthenticated]
    
    def get(self, request):
        try:
            client = Client.objects.select_related('gym').get(user=request.user)
            room = ChatRoom.objects.get(client=client)
        except (Client.DoesNotExist, ChatRoom.DoesNotExist):
            return Response({'messages': []})
            
        limit = int(request.query_params.get('limit', 50))
        offset = int(request.query_params.get('offset', 0))
        
        # Get messages ordered by date desc (newest first for pagination)
        # Usar select_related para evitar N+1 en sender
        messages = ChatMessage.objects.filter(room=room).select_related('sender').order_by('-created_at')[offset:offset+limit]
        
        # Determine strict sender type for UI
        # We need to know if message is from 'ME' (client) or 'THEM' (gym/staff)
        data = []
        for msg in messages:
            is_me = msg.sender == request.user
            
            data.append({
                'id': msg.id,
                'message': msg.message,
                'is_me': is_me,
                'sender_name': 'Yo' if is_me else (msg.sender.get_full_name() or 'Staff'),
                'created_at': msg.created_at.isoformat(),
                'is_read': msg.is_read,
                'attachment_url': msg.attachment.url if msg.attachment else None,
            })
            
        return Response({'success': True, 'messages': data}) # Returns newest first

    def post(self, request):
        try:
            client = Client.objects.get(user=request.user)
            # Ensure room exists
            room, _ = ChatRoom.objects.get_or_create(
                client=client,
                defaults={'gym': client.gym}
            )
        except Client.DoesNotExist:
            return Response(
                {'error': 'Usuario no es un cliente'},
                status=status.HTTP_403_FORBIDDEN
            )
            
        content = request.data.get('message')
        if not content:
            return Response(
                {'error': 'El mensaje no puede estar vacío'},
                status=status.HTTP_400_BAD_REQUEST
            )
            
        # Create message
        msg = ChatMessage.objects.create(
            room=room,
            sender=request.user,
            message=content
        )
        
        # Update room
        room.last_message_at = timezone.now()
        room.save()
        
        return Response({
            'success': True,
            'message': {
                'id': msg.id,
                'message': msg.message,
                'is_me': True,
                'sender_name': 'Yo',
                'created_at': msg.created_at.isoformat(),
                'is_read': False,
            }
        }, status=status.HTTP_201_CREATED)


class MarkReadView(views.APIView):
    """
    Mark messages as read.
    
    POST /api/chat/read/
    """
    permission_classes = [IsAuthenticated]
    
    def post(self, request):
        try:
            client = Client.objects.get(user=request.user)
            room = ChatRoom.objects.get(client=client)
        except (Client.DoesNotExist, ChatRoom.DoesNotExist):
            return Response({'success': False})
            
        # Mark all messages NOT sent by me as read
        ChatMessage.objects.filter(
            room=room
        ).exclude(
            sender=request.user
        ).update(is_read=True)
        
        return Response({'success': True})
