"""
Views for Class Review Reports and Management
"""
from django.shortcuts import render, get_object_or_404, redirect
from django.contrib.auth.decorators import login_required
from django.http import HttpResponse, JsonResponse
from django.db.models import Avg, Count, Q
from django.utils import timezone
from accounts.decorators import require_gym_permission
from datetime import datetime, timedelta
import csv

from activities.models import ClassReview, ReviewRequest, ReviewSettings, ActivitySession
from staff.models import StaffProfile


@login_required
@require_gym_permission("activities.view_classreview")
def review_report(request):
    """
    Report dashboard for class reviews with filtering by staff, date range, etc.
    """
    gym = request.gym
    
    # Get filters from request
    staff_id = request.GET.get('staff')
    date_from = request.GET.get('date_from')
    date_to = request.GET.get('date_to')
    period = request.GET.get('period', 'month')  # day, week, month, custom
    min_rating = request.GET.get('min_rating')
    
    # Base query
    reviews = ClassReview.objects.filter(
        session__gym=gym
    ).select_related(
        'session__activity', 
        'session__staff', 
        'session__staff__user',
        'client'
    ).order_by('-created_at')
    
    # Apply filters
    if staff_id:
        reviews = reviews.filter(session__staff_id=staff_id)
    
    # Date range filtering
    if period == 'day':
        start_date = timezone.now().replace(hour=0, minute=0, second=0, microsecond=0)
        reviews = reviews.filter(created_at__gte=start_date)
    elif period == 'week':
        start_date = timezone.now() - timedelta(days=7)
        reviews = reviews.filter(created_at__gte=start_date)
    elif period == 'month':
        start_date = timezone.now().replace(day=1, hour=0, minute=0, second=0, microsecond=0)
        reviews = reviews.filter(created_at__gte=start_date)
    elif period == 'custom' and date_from and date_to:
        reviews = reviews.filter(
            created_at__date__gte=date_from,
            created_at__date__lte=date_to
        )
    
    if min_rating:
        reviews = reviews.filter(class_rating__gte=float(min_rating))
    
    # Calculate stats
    total_reviews = reviews.count()
    avg_instructor_rating = reviews.aggregate(avg=Avg('instructor_rating'))['avg'] or 0
    avg_class_rating = reviews.aggregate(avg=Avg('class_rating'))['avg'] or 0
    
    # Staff rankings
    staff_stats = reviews.values(
        'session__staff__id',
        'session__staff__user__first_name',
        'session__staff__user__last_name'
    ).annotate(
        total_reviews=Count('id'),
        avg_instructor_rating=Avg('instructor_rating'),
        avg_class_rating=Avg('class_rating')
    ).order_by('-avg_instructor_rating')
    
    # Get all active staff for filter dropdown
    all_staff = StaffProfile.objects.filter(
        gym=gym, 
        is_active=True
    ).select_related('user').order_by('user__first_name')
    
    # Most common tags
    from django.db.models import JSONField
    from collections import Counter
    all_tags = []
    for review in reviews:
        if review.tags:
            all_tags.extend(review.tags)
    tag_counts = Counter(all_tags).most_common(10)
    
    context = {
        'reviews': reviews[:50],  # Limit to recent 50 for page load
        'total_reviews': total_reviews,
        'avg_instructor_rating': round(avg_instructor_rating, 2),
        'avg_class_rating': round(avg_class_rating, 2),
        'staff_stats': staff_stats,
        'all_staff': all_staff,
        'tag_counts': tag_counts,
        'filters': {
            'staff_id': staff_id,
            'date_from': date_from,
            'date_to': date_to,
            'period': period,
            'min_rating': min_rating,
        }
    }
    
    return render(request, 'backoffice/activities/review_report.html', context)


@login_required
@require_gym_permission("activities.view_classreview")
def export_reviews_csv(request):
    """
    Export reviews to CSV with same filters as report
    """
    gym = request.gym
    
    # Apply same filters as report
    staff_id = request.GET.get('staff')
    date_from = request.GET.get('date_from')
    date_to = request.GET.get('date_to')
    period = request.GET.get('period', 'month')
    
    reviews = ClassReview.objects.filter(
        session__gym=gym
    ).select_related(
        'session__activity', 
        'session__staff__user',
        'client'
    ).order_by('-created_at')
    
    if staff_id:
        reviews = reviews.filter(session__staff_id=staff_id)
    
    if period == 'day':
        start_date = timezone.now().replace(hour=0, minute=0, second=0, microsecond=0)
        reviews = reviews.filter(created_at__gte=start_date)
    elif period == 'week':
        start_date = timezone.now() - timedelta(days=7)
        reviews = reviews.filter(created_at__gte=start_date)
    elif period == 'month':
        start_date = timezone.now().replace(day=1, hour=0, minute=0, second=0, microsecond=0)
        reviews = reviews.filter(created_at__gte=start_date)
    elif period == 'custom' and date_from and date_to:
        reviews = reviews.filter(
            created_at__date__gte=date_from,
            created_at__date__lte=date_to
        )
    
    # Create CSV response
    response = HttpResponse(content_type='text/csv; charset=utf-8')
    response['Content-Disposition'] = f'attachment; filename="reviews_{timezone.now().strftime("%Y%m%d")}.csv"'
    
    writer = csv.writer(response)
    writer.writerow([
        'Fecha',
        'Cliente',
        'Actividad',
        'Instructor',
        'Rating Instructor',
        'Rating Clase',
        'Etiquetas',
        'Comentario',
        'Aprobado',
        'Público'
    ])
    
    for review in reviews:
        writer.writerow([
            review.created_at.strftime('%Y-%m-%d %H:%M'),
            f"{review.client.first_name} {review.client.last_name}",
            review.session.activity.name,
            f"{review.session.staff.user.first_name} {review.session.staff.user.last_name}",
            review.instructor_rating,
            review.class_rating,
            ', '.join(review.tags) if review.tags else '',
            review.comment or '',
            'Sí' if review.is_approved else 'No',
            'Sí' if review.is_public else 'No'
        ])
    
    return response


@login_required
@require_gym_permission("activities.change_classreview")
def toggle_review_approval(request, review_id):
    """
    Toggle approval status of a review
    """
    review = get_object_or_404(ClassReview, id=review_id, session__gym=request.gym)
    review.is_approved = not review.is_approved
    review.save()
    
    return JsonResponse({
        'success': True,
        'is_approved': review.is_approved
    })


@login_required
@require_gym_permission("activities.change_classreview")
def toggle_review_public(request, review_id):
    """
    Toggle public visibility of a review
    """
    review = get_object_or_404(ClassReview, id=review_id, session__gym=request.gym)
    review.is_public = not review.is_public
    review.save()
    
    return JsonResponse({
        'success': True,
        'is_public': review.is_public
    })


@login_required
@require_gym_permission("activities.change_reviewsettings")
def review_settings_view(request):
    """
    Configure ReviewSettings for the gym
    """
    gym = request.gym
    settings, created = ReviewSettings.objects.get_or_create(gym=gym)
    
    if request.method == 'POST':
        settings.enabled = request.POST.get('enabled') == 'on'
        settings.delay_hours = int(request.POST.get('delay_hours', 3))
        settings.request_mode = request.POST.get('request_mode', 'RANDOM')
        settings.random_probability = float(request.POST.get('random_probability', 30))
        settings.points_per_review = int(request.POST.get('points_per_review', 10))
        settings.save()
        
        return JsonResponse({
            'success': True,
            'message': 'Configuración guardada correctamente'
        })
    
    context = {
        'settings': settings
    }
    
    return render(request, 'backoffice/activities/review_settings.html', context)
