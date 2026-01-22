from django.contrib.auth.decorators import login_required
from django.shortcuts import render, redirect, get_object_or_404
from django.contrib import messages
from django.utils import timezone
from django.http import JsonResponse


@login_required
def portal_submit_review(request, request_id):
    """
    Formulario para dejar valoración de una clase.
    """
    if not hasattr(request.user, 'client_profile'):
        return redirect('portal_login')
    
    client = request.user.client_profile
    from activities.models import ReviewRequest, ClassReview
    
    # Obtener solicitud de review
    review_request = get_object_or_404(
        ReviewRequest,
        id=request_id,
        client=client,
        status='PENDING'
    )
    
    # Verificar que no esté expirada
    if timezone.now() > review_request.expires_at:
        review_request.status = 'EXPIRED'
        review_request.save()
        messages.error(request, 'Esta solicitud de valoración ha expirado.')
        return redirect('portal_home')
    
    # Verificar que no haya dejado ya una review
    if ClassReview.objects.filter(session=review_request.session, client=client).exists():
        messages.info(request, 'Ya has valorado esta clase.')
        return redirect('portal_home')
    
    if request.method == 'POST':
        import json
        
        instructor_rating = request.POST.get('instructor_rating')
        class_rating = request.POST.get('class_rating')
        comment = request.POST.get('comment', '').strip()
        tags_json = request.POST.get('tags', '[]')
        
        # Validar
        if not instructor_rating or not class_rating:
            messages.error(request, 'Debes valorar tanto al instructor como la clase.')
            return render(request, 'portal/reviews/submit.html', {
                'client': client,
                'review_request': review_request
            })
        
        try:
            instructor_rating = int(instructor_rating)
            class_rating = int(class_rating)
            
            if not (1 <= instructor_rating <= 5) or not (1 <= class_rating <= 5):
                raise ValueError("Valoración fuera de rango")
            
            # Parsear tags
            try:
                tags = json.loads(tags_json)
            except:
                tags = []
            
            # Crear review
            review = ClassReview.objects.create(
                gym=client.gym,
                session=review_request.session,
                client=client,
                staff=review_request.session.staff,
                instructor_rating=instructor_rating,
                class_rating=class_rating,
                comment=comment,
                tags=tags
            )
            
            # Marcar solicitud como completada
            review_request.status = 'COMPLETED'
            review_request.completed_at = timezone.now()
            review_request.save()
            
            messages.success(request, '¡Gracias por tu valoración! 🎉')
            return redirect('portal_home')
            
        except ValueError:
            messages.error(request, 'Valoraciones inválidas.')
    
    context = {
        'client': client,
        'review_request': review_request,
    }
    return render(request, 'portal/reviews/submit.html', context)
