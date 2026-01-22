"""
API Views for Client Class History and Reviews (Mobile App).
View past classes and submit reviews.
"""
from rest_framework import views, status
from rest_framework.response import Response
from rest_framework.permissions import IsAuthenticated
from django.utils import timezone

from clients.models import Client
from activities.models import ActivitySessionBooking, ClassReview, ActivitySession
from staff.models import StaffProfile

class ClassHistoryView(views.APIView):
    """
    List past classes (attended or not).
    
    GET /api/history/classes/?limit=20&offset=0
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
            
        limit = int(request.query_params.get('limit', 20))
        offset = int(request.query_params.get('offset', 0))
        
        # Past bookings (session end_datetime < now)
        now = timezone.now()
        
        bookings = ActivitySessionBooking.objects.filter(
            client=client,
            session__end_datetime__lt=now
        ).select_related('session', 'session__activity', 'session__staff').order_by('-session__start_datetime')[offset:offset+limit]
        
        data = []
        for booking in bookings:
            session = booking.session
            
            # Check if review exists
            has_review = ClassReview.objects.filter(client=client, session=session).exists()
            
            data.append({
                'booking_id': booking.id,
                'session_id': session.id,
                'activity_name': session.activity.name,
                'start_datetime': session.start_datetime.isoformat(),
                'end_datetime': session.end_datetime.isoformat(),
                'staff_name': session.staff.user.get_full_name() if session.staff else 'Staff',
                'status': booking.status,
                'attended': booking.attended,
                'has_review': has_review
            })
            
        return Response({
            'classes': data
        })


class SubmitReviewView(views.APIView):
    """
    Submit a review for a past class.
    
    POST /api/history/reviews/
    Body:
    {
        "session_id": 123,
        "instructor_rating": 5,
        "class_rating": 5,
        "comment": "Optional"
    }
    """
    permission_classes = [IsAuthenticated]
    
    def post(self, request):
        try:
            client = Client.objects.get(user=request.user)
        except Client.DoesNotExist:
            return Response({'error': 'No cliente'}, status=403)
            
        session_id = request.data.get('session_id')
        instructor_rating = request.data.get('instructor_rating')
        class_rating = request.data.get('class_rating')
        comment = request.data.get('comment', '')
        
        if not all([session_id, instructor_rating, class_rating]):
            return Response({'error': 'Faltan datos'}, status=400)
            
        try:
            session = ActivitySession.objects.get(id=session_id)
        except ActivitySession.DoesNotExist:
             return Response({'error': 'Sesión no encontrada'}, status=404)
        
        # Valida asistencia o booking
        has_booking = ActivitySessionBooking.objects.filter(client=client, session=session).exists()
        if not has_booking:
             return Response({'error': 'No asististe a esta clase'}, status=403)
             
        # Check duplicate
        if ClassReview.objects.filter(client=client, session=session).exists():
             return Response({'error': 'Ya valoraste esta clase'}, status=400)
             
        # Create review
        # Staff is required in model, take session staff or fail safely if none (though model says not null usually, let's check model definition... 
        # ActivitySession staff is nullable. ClassReview staff is NOT nullable.
        # If session has no staff, we can't create ClassReview easily unless we have a 'default' staff or changes model.
        # Let's assume sessions have staff, or handle edge case.
        
        staff = session.staff
        if not staff:
             # Find administrative staff or fail
             # For MVP, if no staff assigned to session, we can't rate 'instructor'.
             # Hack: find any staff or fail.
             return Response({'error': 'Esta sesión no tiene instructor asignado para valorar'}, status=400)

        review = ClassReview.objects.create(
            gym=session.gym,
            session=session,
            client=client,
            staff=staff,
            instructor_rating=instructor_rating,
            class_rating=class_rating,
            comment=comment,
            is_approved=False # Pending approval
        )
        
        return Response({'success': True, 'message': 'Review enviada'})
