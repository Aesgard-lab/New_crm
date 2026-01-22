from rest_framework import serializers
from organizations.models import Gym
from accounts.models import User
from clients.models import Client, ClientMembership

class GymSerializer(serializers.ModelSerializer):
    class Meta:
        model = Gym
        fields = ['id', 'name', 'city', 'address', 'brand_color', 'phone', 'logo']

class UserSerializer(serializers.ModelSerializer):
    class Meta:
        model = User
        fields = ['email', 'first_name', 'last_name']

class ClientMembershipSerializer(serializers.ModelSerializer):
    plan_name = serializers.CharField(source='plan.name', read_only=True)
    
    class Meta:
        model = ClientMembership
        fields = ['status', 'plan_name', 'end_date']

class ClientProfileSerializer(serializers.ModelSerializer):
    user = UserSerializer(read_only=True)
    active_membership = serializers.SerializerMethodField()
    gym_name = serializers.CharField(source='gym.name', read_only=True)
    phone = serializers.CharField(source='phone_number', read_only=True)
    next_bookings = serializers.SerializerMethodField()
    stats = serializers.SerializerMethodField()
    birth_date_formatted = serializers.SerializerMethodField()
    client_type_display = serializers.SerializerMethodField()
    
    class Meta:
        model = Client
        fields = [
            'id', 'gym_name', 'first_name', 'last_name', 'email', 'phone',
            'dni', 'birth_date', 'birth_date_formatted', 'address', 'client_type', 'client_type_display',
            'user', 'photo', 'access_code', 'active_membership', 
            'next_bookings', 'stats'
        ]
    
    def get_birth_date_formatted(self, obj):
        if obj.birth_date:
            return obj.birth_date.strftime('%d/%m/%Y')
        return ''
    
    def get_client_type_display(self, obj):
        if hasattr(obj, 'client_type') and obj.client_type:
            return obj.get_client_type_display()
        return ''

    def get_active_membership(self, obj):
        membership = obj.memberships.filter(status='ACTIVE').first()
        if membership:
            data = ClientMembershipSerializer(membership).data
            # Add expires_at field
            if membership.end_date:
                data['expires_at'] = membership.end_date.strftime('%d/%m/%Y')
            return data
        return None

    def get_next_bookings(self, obj):
        from django.utils import timezone
        from activities.models import ActivitySessionBooking
        
        try:
            now = timezone.now()
            bookings = ActivitySessionBooking.objects.filter(
                client=obj,
                status='CONFIRMED'
            ).select_related('session', 'session__activity', 'session__staff__user').order_by('session__date', 'session__start_time')[:10]
            
            # Filter by date in Python since session is ActivitySession
            future_bookings = [b for b in bookings if b.session and b.session.date >= now.date()][:3]
            
            result = []
            for booking in future_bookings:
                session = booking.session
                if session and session.activity:
                    result.append({
                        'id': booking.id,
                        'activity_name': session.activity.name,
                        'date': session.date.strftime('%d/%m/%Y'),
                        'time': session.start_time.strftime('%H:%M') if session.start_time else '',
                        'instructor': session.staff.user.first_name if session.staff and session.staff.user else 'Sin instructor'
                    })
            return result
        except Exception as e:
            # Return empty list on error to prevent login failures
            return []

    def get_stats(self, obj):
        from django.utils import timezone
        from datetime import timedelta
        from clients.models import ClientVisit
        from activities.models import ActivitySessionBooking
        
        try:
            now = timezone.now()
            today = now.date()
            first_day_of_month = today.replace(day=1)
            
            # Filter visits this month using __date lookup for DateTimeField
            monthly_visits = ClientVisit.objects.filter(
                client=obj,
                check_in_time__date__gte=first_day_of_month
            ).count()
            
            # Total visits
            total_visits = ClientVisit.objects.filter(client=obj).count()
            
            # Streak - consecutive days with visits or attended bookings
            current_streak = 0
            check_date = today
            for i in range(30):
                # Check visits for this date using __date lookup
                has_visit = ClientVisit.objects.filter(
                    client=obj,
                    check_in_time__date=check_date
                ).exists()
                
                # Check attended classes for this date
                has_attended = ActivitySessionBooking.objects.filter(
                    client=obj,
                    session__date=check_date,
                    attended=True
                ).exists()
                
                if has_visit or has_attended:
                    current_streak += 1
                    check_date -= timedelta(days=1)
                else:
                    break
            
            # Monthly classes attended
            monthly_classes = ActivitySessionBooking.objects.filter(
                client=obj,
                session__date__gte=first_day_of_month,
                attended=True
            ).count()
            
            return {
                'monthly_visits': monthly_visits,
                'current_streak': current_streak,
                'total_visits': total_visits,
                'monthly_classes': monthly_classes,
            }
        except Exception as e:
            # Return default stats on error to prevent login failures
            return {
                'monthly_visits': 0,
                'current_streak': 0,
                'total_visits': 0,
                'monthly_classes': 0,
            }


# ===========================
# SCHEDULE & BOOKINGS
# ===========================

class ActivitySerializer(serializers.ModelSerializer):
    """Serializer for Activity (type of class)"""
    class Meta:
        from activities.models import Activity
        model = Activity
        fields = ['id', 'name', 'description', 'color']


class InstructorSerializer(serializers.ModelSerializer):
    """Serializer for Staff/Instructor"""
    full_name = serializers.SerializerMethodField()
    email = serializers.SerializerMethodField()
    
    class Meta:
        from staff.models import StaffProfile
        model = StaffProfile
        fields = ['id', 'full_name', 'email']
    
    def get_full_name(self, obj):
        if hasattr(obj.user, 'get_full_name'):
            return obj.user.get_full_name()
        return f"{obj.user.first_name} {obj.user.last_name}".strip() or obj.user.username
    
    def get_email(self, obj):
        return obj.user.email


class ActivitySessionSerializer(serializers.ModelSerializer):
    """Serializer for ActivitySession (specific class instance)"""
    activity = ActivitySerializer(read_only=True)
    instructor = InstructorSerializer(source='staff', read_only=True)
    available_spots = serializers.SerializerMethodField()
    is_booked = serializers.SerializerMethodField()
    gym = serializers.SerializerMethodField()
    
    class Meta:
        from activities.models import ActivitySession
        model = ActivitySession
        fields = [
            'id', 'activity', 'instructor', 'start_datetime', 'end_datetime',
            'max_capacity', 'available_spots', 'is_booked', 'gym'
        ]
    
    def get_available_spots(self, obj):
        """Calculate available spots"""
        from activities.models import ActivitySessionBooking
        booked = ActivitySessionBooking.objects.filter(
            session=obj,
            status='CONFIRMED'
        ).count()
        return max(0, obj.max_capacity - booked)
    
    def get_is_booked(self, obj):
        """Check if current user has booked this session"""
        request = self.context.get('request')
        if not request or not request.user.is_authenticated:
            return False
        
        try:
            from clients.models import Client
            from activities.models import ActivitySessionBooking
            client = Client.objects.get(user=request.user)
            return ActivitySessionBooking.objects.filter(
                session=obj,
                client=client,
                status='CONFIRMED'
            ).exists()
        except Client.DoesNotExist:
            return False
    
    def get_gym(self, obj):
        """Return gym info for cross-booking context"""
        gym = obj.activity.gym
        return {
            'id': gym.id,
            'name': gym.commercial_name or gym.name,
            'city': gym.city
        }


class BookingSerializer(serializers.ModelSerializer):
    """Serializer for ActivitySessionBooking"""
    session = ActivitySessionSerializer(read_only=True)
    activity_name = serializers.CharField(source='session.activity.name', read_only=True)
    instructor_name = serializers.SerializerMethodField()
    
    class Meta:
        from activities.models import ActivitySessionBooking
        model = ActivitySessionBooking
        fields = [
            'id', 'session', 'activity_name', 'instructor_name',
            'status', 'booked_at', 'attended'
        ]
    
    def get_instructor_name(self, obj):
        if obj.session and obj.session.staff and obj.session.staff.user:
            user = obj.session.staff.user
            full_name = f"{user.first_name} {user.last_name}".strip()
            return full_name or user.username
        return "Sin instructor"

