from rest_framework import views, generics, status
from rest_framework.response import Response
from rest_framework.permissions import IsAuthenticated
from django.utils import timezone
from django.db.models import Q
from datetime import datetime, timedelta

from activities.models import Activity, ActivitySession, ActivitySessionBooking, WaitlistEntry
from clients.models import Client, ClientMembership
from organizations.models import Gym
from .serializers import (
    ActivitySerializer,
    ActivitySessionSerializer,
    BookingSerializer
)


class ScheduleView(generics.ListAPIView):
    """
    Get schedule of classes for a date range.
    Query params:
    - start_date: YYYY-MM-DD (default: today)
    - end_date: YYYY-MM-DD (default: today + 7 days)
    - activity_id: Filter by activity (optional)
    - gym_id: Filter by specific gym (optional, for cross-booking)
    - cross_booking: Include other franchise gyms (optional, 'true')
    """
    permission_classes = [IsAuthenticated]
    serializer_class = ActivitySessionSerializer
    
    def get_queryset(self):
        # Get client's gym
        try:
            client = Client.objects.get(user=self.request.user)
            gym = client.gym
        except Client.DoesNotExist:
            return ActivitySession.objects.none()
        
        # Parse date range
        start_date_str = self.request.query_params.get('start_date')
        end_date_str = self.request.query_params.get('end_date')
        
        if start_date_str:
            start_date = datetime.strptime(start_date_str, '%Y-%m-%d').date()
        else:
            start_date = timezone.now().date()
        
        if end_date_str:
            end_date = datetime.strptime(end_date_str, '%Y-%m-%d').date()
        else:
            end_date = start_date + timedelta(days=7)
        
        # Determine which gyms to include
        gym_ids = [gym.id]
        cross_booking = self.request.query_params.get('cross_booking', 'false').lower() == 'true'
        specific_gym_id = self.request.query_params.get('gym_id')
        
        # Check if franchise allows cross-booking
        if cross_booking and gym.franchise and gym.franchise.allow_cross_booking:
            franchise_gym_ids = list(gym.franchise.gyms.values_list('id', flat=True))
            gym_ids = franchise_gym_ids
        
        # If specific gym requested and it's in the franchise, use only that gym
        if specific_gym_id:
            try:
                specific_gym = Gym.objects.get(id=specific_gym_id)
                # Validate: must be same gym or in same franchise with cross-booking enabled
                if specific_gym.id == gym.id:
                    gym_ids = [specific_gym.id]
                elif gym.franchise and gym.franchise.allow_cross_booking and specific_gym.franchise == gym.franchise:
                    gym_ids = [specific_gym.id]
            except Gym.DoesNotExist:
                pass
        
        # Build queryset
        queryset = ActivitySession.objects.filter(
            activity__gym_id__in=gym_ids,
            start_datetime__date__gte=start_date,
            start_datetime__date__lte=end_date
        ).exclude(status='CANCELLED').select_related('activity', 'staff', 'activity__gym').order_by('start_datetime')
        
        # Filter by activity if specified
        activity_id = self.request.query_params.get('activity_id')
        if activity_id:
            queryset = queryset.filter(activity_id=activity_id)
        
        return queryset
    
    def get_serializer_context(self):
        context = super().get_serializer_context()
        context['request'] = self.request
        return context


class ActivitiesView(generics.ListAPIView):
    """Get list of all activities for filtering"""
    permission_classes = [IsAuthenticated]
    serializer_class = ActivitySerializer
    
    def get_queryset(self):
        try:
            client = Client.objects.get(user=self.request.user)
            return Activity.objects.filter(gym=client.gym)
        except Client.DoesNotExist:
            return Activity.objects.none()


class BookSessionView(views.APIView):
    """
    Book a session.
    POST data: { "session_id": 123 }
    Supports cross-booking if franchise allows it.
    """
    permission_classes = [IsAuthenticated]
    
    def post(self, request):
        session_id = request.data.get('session_id')
        
        if not session_id:
            return Response(
                {'error': 'session_id es requerido'},
                status=status.HTTP_400_BAD_REQUEST
            )
        
        # Get client
        try:
            client = Client.objects.get(user=request.user)
        except Client.DoesNotExist:
            return Response(
                {'error': 'Usuario no es un cliente'},
                status=status.HTTP_403_FORBIDDEN
            )
        
        # Get session
        try:
            session = ActivitySession.objects.select_related('activity__gym', 'activity__gym__franchise').get(id=session_id)
        except ActivitySession.DoesNotExist:
            return Response(
                {'error': 'Sesión no encontrada'},
                status=status.HTTP_404_NOT_FOUND
            )
        
        # Verify cross-booking permission
        session_gym = session.activity.gym
        client_gym = client.gym
        
        if session_gym.id != client_gym.id:
            # Cross-booking attempt - check if allowed
            can_cross_book = (
                client_gym.franchise and 
                session_gym.franchise and 
                client_gym.franchise_id == session_gym.franchise_id and
                client_gym.franchise.allow_cross_booking
            )
            
            if not can_cross_book:
                return Response(
                    {'error': 'No puedes reservar clases en otros gimnasios'},
                    status=status.HTTP_403_FORBIDDEN
                )
        
        # Verify session is in the future
        if session.start_datetime < timezone.now():
            return Response(
                {'error': 'No puedes reservar una clase que ya comenzó'},
                status=status.HTTP_400_BAD_REQUEST
            )
        
        # Verify session is not cancelled
        if session.status == 'CANCELLED':
            return Response(
                {'error': 'Esta clase ha sido cancelada'},
                status=status.HTTP_400_BAD_REQUEST
            )
        
        # Check if already booked
        existing_booking = ActivitySessionBooking.objects.filter(
            session=session,
            client=client,
            status='CONFIRMED'
        ).first()
        
        if existing_booking:
            return Response(
                {'error': 'Ya tienes una reserva para esta clase'},
                status=status.HTTP_400_BAD_REQUEST
            )
        
        # Check capacity
        confirmed_bookings = ActivitySessionBooking.objects.filter(
            session=session,
            status='CONFIRMED'
        ).count()
        
        if confirmed_bookings >= session.max_capacity:
            return Response(
                {'error': 'Esta clase está llena'},
                status=status.HTTP_400_BAD_REQUEST
            )
        
        # Check membership status - allow ACTIVE or PENDING_PAYMENT (if gym config allows)
        valid_statuses = ['ACTIVE']
        if client_gym.allow_booking_with_pending_payment:
            valid_statuses.append('PENDING_PAYMENT')
        
        has_valid_membership = client.memberships.filter(status__in=valid_statuses).exists()
        
        if not has_valid_membership:
            # Check if they have a pending payment membership but the gym doesn't allow booking
            has_pending_payment = client.memberships.filter(status='PENDING_PAYMENT').exists()
            if has_pending_payment:
                return Response(
                    {'error': 'Tu membresía tiene un pago pendiente. Contacta con el gimnasio para regularizar tu situación.'},
                    status=status.HTTP_403_FORBIDDEN
                )
            return Response(
                {'error': 'Necesitas una membresía activa para reservar clases'},
                status=status.HTTP_403_FORBIDDEN
            )
        
        # Handle spot booking if requested
        spot_number = request.data.get('spot_number')
        if spot_number:
            # Verify spot is available
            spot_taken = ActivitySessionBooking.objects.filter(
                session=session,
                spot_number=spot_number,
                status__in=['CONFIRMED', 'PENDING']
            ).exists()
            if spot_taken:
                return Response(
                    {'error': f'El puesto {spot_number} ya está ocupado'},
                    status=status.HTTP_400_BAD_REQUEST
                )
        
        # Create booking
        booking = ActivitySessionBooking.objects.create(
            session=session,
            client=client,
            status='CONFIRMED',
            booked_at=timezone.now(),
            spot_number=spot_number
        )
        
        serializer = BookingSerializer(booking)
        return Response({
            'message': 'Reserva creada exitosamente',
            'booking': serializer.data
        }, status=status.HTTP_201_CREATED)


class CancelBookingView(views.APIView):
    """
    Cancel a booking.
    DELETE /api/bookings/<booking_id>/cancel/
    """
    permission_classes = [IsAuthenticated]
    
    def delete(self, request, booking_id):
        # Get client
        try:
            client = Client.objects.get(user=request.user)
        except Client.DoesNotExist:
            return Response(
                {'error': 'Usuario no es un cliente'},
                status=status.HTTP_403_FORBIDDEN
            )
        
        # Get booking
        try:
            booking = ActivitySessionBooking.objects.get(
                id=booking_id,
                client=client
            )
        except ActivitySessionBooking.DoesNotExist:
            return Response(
                {'error': 'Reserva no encontrada'},
                status=status.HTTP_404_NOT_FOUND
            )
        
        # Check if session is in the future
        if booking.session.start_datetime < timezone.now():
            return Response(
                {'error': 'No puedes cancelar una clase que ya comenzó'},
                status=status.HTTP_400_BAD_REQUEST
            )
        
        # Check if already cancelled
        if booking.status == 'CANCELLED':
            return Response(
                {'error': 'Esta reserva ya está cancelada'},
                status=status.HTTP_400_BAD_REQUEST
            )
        
        # Cancel booking
        booking.status = 'CANCELLED'
        booking.save()
        
        return Response({
            'message': 'Reserva cancelada exitosamente'
        })


class MyBookingsView(generics.ListAPIView):
    """
    Get user's bookings.
    Query params:
    - status: 'upcoming' or 'past' (default: 'upcoming')
    """
    permission_classes = [IsAuthenticated]
    serializer_class = BookingSerializer
    
    def get_queryset(self):
        try:
            client = Client.objects.get(user=self.request.user)
        except Client.DoesNotExist:
            return ActivitySessionBooking.objects.none()
        
        status_filter = self.request.query_params.get('status', 'upcoming')
        
        queryset = ActivitySessionBooking.objects.filter(
            client=client
        ).select_related('session__activity', 'session__staff')
        
        if status_filter == 'upcoming':
            queryset = queryset.filter(
                session__start_datetime__gte=timezone.now(),
                status='CONFIRMED'
            ).order_by('session__start_datetime')
        elif status_filter == 'past':
            queryset = queryset.filter(
                session__start_datetime__lt=timezone.now()
            ).order_by('-session__start_datetime')
        
        return queryset


class FranchiseGymsView(views.APIView):
    """
    Get list of gyms available for cross-booking in the same franchise.
    Returns empty list if cross-booking is not enabled.
    """
    permission_classes = [IsAuthenticated]
    
    def get(self, request):
        try:
            client = Client.objects.get(user=request.user)
        except Client.DoesNotExist:
            return Response({'gyms': [], 'cross_booking_enabled': False})
        
        gym = client.gym
        
        # Check if franchise allows cross-booking
        if not gym.franchise or not gym.franchise.allow_cross_booking:
            return Response({
                'gyms': [],
                'cross_booking_enabled': False,
                'current_gym': {
                    'id': gym.id,
                    'name': gym.commercial_name or gym.name
                }
            })
        
        # Get all gyms in the franchise
        franchise_gyms = gym.franchise.gyms.all()
        
        gyms_data = [{
            'id': g.id,
            'name': g.commercial_name or g.name,
            'address': g.address,
            'city': g.city,
            'is_current': g.id == gym.id
        } for g in franchise_gyms]
        
        return Response({
            'gyms': gyms_data,
            'cross_booking_enabled': True,
            'franchise_name': gym.franchise.name,
            'current_gym': {
                'id': gym.id,
                'name': gym.commercial_name or gym.name
            }
        })


class JoinWaitlistView(views.APIView):
    """
    Join the waitlist for a full class.
    POST /api/waitlist/join/
    Body: { "session_id": 123 }
    """
    permission_classes = [IsAuthenticated]
    
    def post(self, request):
        from activities.session_api import is_client_vip
        
        try:
            client = Client.objects.get(user=request.user)
        except Client.DoesNotExist:
            return Response(
                {'error': 'Usuario no es un cliente'},
                status=status.HTTP_403_FORBIDDEN
            )
        
        session_id = request.data.get('session_id')
        if not session_id:
            return Response(
                {'error': 'session_id es requerido'},
                status=status.HTTP_400_BAD_REQUEST
            )
        
        try:
            session = ActivitySession.objects.get(id=session_id)
        except ActivitySession.DoesNotExist:
            return Response(
                {'error': 'Sesión no encontrada'},
                status=status.HTTP_404_NOT_FOUND
            )
        
        # Verify policy allows waitlist
        policy = session.activity.policy
        if not policy or not policy.waitlist_enabled:
            return Response(
                {'error': 'Esta clase no permite lista de espera'},
                status=status.HTTP_400_BAD_REQUEST
            )
        
        # Check if already in class
        if session.attendees.filter(pk=client.pk).exists():
            return Response(
                {'error': 'Ya estás en esta clase'},
                status=status.HTTP_400_BAD_REQUEST
            )
        
        # Check if already in waitlist
        if WaitlistEntry.objects.filter(session=session, client=client, status__in=['WAITING', 'NOTIFIED']).exists():
            return Response(
                {'error': 'Ya estás en la lista de espera'},
                status=status.HTTP_400_BAD_REQUEST
            )
        
        # Check waitlist limit
        if policy.waitlist_limit > 0:
            current_count = WaitlistEntry.objects.filter(session=session, status__in=['WAITING', 'NOTIFIED']).count()
            if current_count >= policy.waitlist_limit:
                return Response(
                    {'error': 'La lista de espera está llena'},
                    status=status.HTTP_400_BAD_REQUEST
                )
        
        # Check if client is VIP
        client_is_vip = is_client_vip(client, policy)
        
        # Create entry
        entry = WaitlistEntry.objects.create(
            session=session,
            client=client,
            gym=client.gym,
            status='WAITING',
            is_vip=client_is_vip
        )
        
        # Calculate position
        position = WaitlistEntry.objects.filter(
            session=session,
            status__in=['WAITING', 'NOTIFIED'],
            joined_at__lt=entry.joined_at
        ).count() + 1
        
        if client_is_vip:
            # VIPs count position among VIPs only
            position = WaitlistEntry.objects.filter(
                session=session,
                status__in=['WAITING', 'NOTIFIED'],
                is_vip=True,
                joined_at__lt=entry.joined_at
            ).count() + 1
        
        return Response({
            'message': 'Te has unido a la lista de espera',
            'entry_id': entry.id,
            'position': position,
            'is_vip': client_is_vip,
            'waitlist_mode': policy.waitlist_mode
        }, status=status.HTTP_201_CREATED)


class LeaveWaitlistView(views.APIView):
    """
    Leave the waitlist for a class.
    DELETE /api/waitlist/<entry_id>/leave/
    """
    permission_classes = [IsAuthenticated]
    
    def delete(self, request, entry_id):
        try:
            client = Client.objects.get(user=request.user)
        except Client.DoesNotExist:
            return Response(
                {'error': 'Usuario no es un cliente'},
                status=status.HTTP_403_FORBIDDEN
            )
        
        try:
            entry = WaitlistEntry.objects.get(id=entry_id, client=client, status__in=['WAITING', 'NOTIFIED'])
        except WaitlistEntry.DoesNotExist:
            return Response(
                {'error': 'Entrada de lista de espera no encontrada'},
                status=status.HTTP_404_NOT_FOUND
            )
        
        entry.status = 'CANCELLED'
        entry.save()
        
        return Response({
            'message': 'Has salido de la lista de espera'
        })


class ClaimWaitlistSpotView(views.APIView):
    """
    Claim an available spot from the waitlist.
    Used when in BROADCAST or FIRST_CLAIM mode after being notified.
    POST /api/waitlist/<entry_id>/claim/
    """
    permission_classes = [IsAuthenticated]
    
    def post(self, request, entry_id):
        try:
            client = Client.objects.get(user=request.user)
        except Client.DoesNotExist:
            return Response(
                {'error': 'Usuario no es un cliente'},
                status=status.HTTP_403_FORBIDDEN
            )
        
        try:
            entry = WaitlistEntry.objects.get(id=entry_id, client=client, status__in=['WAITING', 'NOTIFIED'])
        except WaitlistEntry.DoesNotExist:
            return Response(
                {'error': 'Entrada de lista de espera no encontrada o ya procesada'},
                status=status.HTTP_404_NOT_FOUND
            )
        
        session = entry.session
        
        # Check if claim has expired
        if entry.claim_expires_at and timezone.now() > entry.claim_expires_at:
            entry.status = 'EXPIRED'
            entry.save()
            return Response(
                {'error': 'El tiempo para reclamar la plaza ha expirado'},
                status=status.HTTP_400_BAD_REQUEST
            )
        
        # Check if there's space
        confirmed_count = ActivitySessionBooking.objects.filter(
            session=session,
            status='CONFIRMED'
        ).count()
        
        if confirmed_count >= session.max_capacity:
            return Response(
                {'error': 'Lo sentimos, la plaza ya fue reclamada por otro cliente',
                 'code': 'SPOT_TAKEN'},
                status=status.HTTP_409_CONFLICT
            )
        
        # Add to class
        session.attendees.add(client)
        
        # Update waitlist entry
        entry.status = 'PROMOTED'
        entry.promoted_at = timezone.now()
        entry.claimed_at = timezone.now()
        entry.save()
        
        # Create booking
        booking = ActivitySessionBooking.objects.create(
            session=session,
            client=client,
            status='CONFIRMED',
            attendance_status='PENDING'
        )
        
        # Send notification
        try:
            from marketing.signals import send_class_notification
            send_class_notification(
                client=client,
                event_type='WAITLIST_PROMOTED',
                session=session
            )
        except Exception:
            pass
        
        return Response({
            'message': '¡Plaza reclamada con éxito! Ya estás en la clase.',
            'booking_id': booking.id,
            'session': {
                'id': session.id,
                'activity_name': session.activity.name,
                'start_datetime': session.start_datetime.isoformat()
            }
        })


class MyWaitlistEntriesView(views.APIView):
    """
    Get all waitlist entries for the current client.
    Includes pending claims that need action.
    GET /api/waitlist/my-entries/
    """
    permission_classes = [IsAuthenticated]
    
    def get(self, request):
        try:
            client = Client.objects.get(user=request.user)
        except Client.DoesNotExist:
            return Response({'entries': []})
        
        entries = WaitlistEntry.objects.filter(
            client=client,
            status__in=['WAITING', 'NOTIFIED'],
            session__start_datetime__gte=timezone.now()
        ).select_related('session', 'session__activity').order_by('session__start_datetime')
        
        result = []
        for entry in entries:
            session = entry.session
            
            # Calculate position
            position = WaitlistEntry.objects.filter(
                session=session,
                status__in=['WAITING', 'NOTIFIED'],
                joined_at__lt=entry.joined_at
            ).count() + 1
            
            if entry.is_vip:
                position = WaitlistEntry.objects.filter(
                    session=session,
                    status__in=['WAITING', 'NOTIFIED'],
                    is_vip=True,
                    joined_at__lt=entry.joined_at
                ).count() + 1
            
            result.append({
                'id': entry.id,
                'session_id': session.id,
                'activity_name': session.activity.name,
                'activity_color': session.activity.color,
                'start_datetime': session.start_datetime.isoformat(),
                'status': entry.status,
                'position': position,
                'is_vip': entry.is_vip,
                'can_claim': entry.status == 'NOTIFIED',
                'claim_expires_at': entry.claim_expires_at.isoformat() if entry.claim_expires_at else None,
                'notified_at': entry.notified_at.isoformat() if entry.notified_at else None,
            })
        
        return Response({'entries': result})


class SessionSpotsView(views.APIView):
    """
    Get available spots for a session.
    GET /api/bookings/session/<session_id>/spots/
    Returns layout with spots (available/occupied/mine status) for spot booking.
    """
    permission_classes = []  # Allow unauthenticated access to see layout
    
    def get(self, request, session_id):
        import json
        
        try:
            session = ActivitySession.objects.select_related('activity', 'room').get(id=session_id)
        except ActivitySession.DoesNotExist:
            return Response({'error': 'Sesión no encontrada'}, status=status.HTTP_404_NOT_FOUND)
        
        activity = session.activity
        room = session.room
        
        # Check if activity allows spot booking
        if not activity.allow_spot_booking:
            return Response({
                'allow_spot_booking': False,
                'message': 'Esta actividad no permite selección de puesto'
            })
        
        # Check if room has layout
        if not room or not room.layout_configuration:
            return Response({
                'allow_spot_booking': True,
                'has_layout': False,
                'message': 'La sala no tiene un layout configurado'
            })
        
        # Parse layout
        try:
            layout_items = room.layout_configuration if isinstance(room.layout_configuration, list) else json.loads(room.layout_configuration)
        except (json.JSONDecodeError, TypeError):
            layout_items = []
        
        # Get occupied spots
        occupied_spots = set(
            ActivitySessionBooking.objects.filter(
                session=session,
                status__in=['CONFIRMED', 'PENDING'],
                spot_number__isnull=False
            ).values_list('spot_number', flat=True)
        )
        
        # Get user's spot if authenticated
        my_spot = None
        if request.user.is_authenticated:
            try:
                client = Client.objects.get(user=request.user)
                my_booking = ActivitySessionBooking.objects.filter(
                    session=session,
                    client=client,
                    status__in=['CONFIRMED', 'PENDING']
                ).first()
                if my_booking and my_booking.spot_number:
                    my_spot = my_booking.spot_number
            except Client.DoesNotExist:
                pass
        
        # Build spots list with status
        spots = []
        for item in layout_items:
            if item.get('type') == 'spot':
                spot_number = item.get('number')
                spot_status = 'available'
                if spot_number in occupied_spots:
                    spot_status = 'mine' if spot_number == my_spot else 'occupied'
                
                spots.append({
                    'number': spot_number,
                    'x': item.get('x'),
                    'y': item.get('y'),
                    'status': spot_status
                })
        
        # Get obstacles
        obstacles = [
            {'x': item.get('x'), 'y': item.get('y')}
            for item in layout_items if item.get('type') == 'obstacle'
        ]
        
        # Calculate layout dimensions
        max_x = max((item.get('x', 0) + 50 for item in layout_items), default=400)
        max_y = max((item.get('y', 0) + 50 for item in layout_items), default=300)
        
        return Response({
            'allow_spot_booking': True,
            'has_layout': True,
            'layout': {
                'width': max_x,
                'height': max_y
            },
            'session_id': session_id,
            'room_name': room.name,
            'activity_name': activity.name,
            'spots': spots,
            'obstacles': obstacles,
            'total_spots': len(spots),
            'available_spots': len([s for s in spots if s['status'] == 'available']),
            'occupied_spots': len([s for s in spots if s['status'] == 'occupied']),
            'my_spot': my_spot
        })
