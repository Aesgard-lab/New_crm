from django.shortcuts import render
from django.contrib.auth.decorators import login_required
from django.http import HttpResponse
from accounts.decorators import require_gym_permission
from organizations.models import Gym
from clients.models import Client, ClientField, ClientTag, ClientGroup, DocumentTemplate
from memberships.models import MembershipPlan
from services.models import Service
from products.models import Product
from django.db.models import Q, Sum, Count, Exists, OuterRef
from datetime import timedelta, date
import csv

def _get_filtered_clients(request):
    """Helper to get filtered clients queryset based on request params."""
    gym_id = request.session.get("current_gym_id")
    if not gym_id:
        return None, None, [], {}, [], [], [], []

    gym = Gym.objects.get(id=gym_id)

    custom_fields = list(
        ClientField.objects.filter(gym=gym, is_active=True)
        .prefetch_related("options")
        .order_by("name")
    )

    # Filtros reales para selects
    membership_plans = MembershipPlan.objects.filter(gym=gym, is_active=True).order_by('name')
    services = Service.objects.filter(gym=gym, is_active=True).order_by('name')
    products = Product.objects.filter(gym=gym, is_active=True).order_by('name')
    document_templates = DocumentTemplate.objects.filter(gym=gym, is_active=True).order_by('name')
    
    custom_field_options = {
        field.slug: ({True: "Sí", False: "No"} if field.field_type == ClientField.FieldType.TOGGLE else {opt.value: opt.label for opt in field.options.all()})
        for field in custom_fields
    }

    # Base Query with total spent annotation
    clients = Client.objects.filter(gym=gym).prefetch_related(
        'tags', 'memberships', 'visits', 'documents'
    ).annotate(
        total_spent=Sum('orders__total_amount', filter=Q(orders__status='PAID'))
    )

    # Filters
    q = request.GET.get('q')
    if q:
        clients = clients.filter(
            Q(first_name__icontains=q) | 
            Q(last_name__icontains=q) | 
            Q(email__icontains=q) |
            Q(phone_number__icontains=q)
        )

    status = request.GET.get('status')
    if status and status != 'all':
        clients = clients.filter(status=status)

    company = request.GET.get('company')
    if company == 'company':
        clients = clients.filter(is_company_client=True)
    elif company == 'individual':
        clients = clients.filter(is_company_client=False)

    selected_tags = request.GET.getlist('tags')
    if selected_tags:
        clients = clients.filter(tags__id__in=selected_tags).distinct()

    # Filtro por tipo de cuota (ahora múltiple)
    plan_ids = request.GET.getlist('membership_plan')
    if plan_ids and 'all' not in plan_ids:
        clients = clients.filter(memberships__plan_id__in=plan_ids).distinct()

    # Filtro por servicio (ahora múltiple)
    service_ids = request.GET.getlist('service')
    if service_ids and 'all' not in service_ids:
        service_names = list(Service.objects.filter(id__in=service_ids).values_list('name', flat=True))
        q_services = Q()
        for name in service_names:
            q_services |= Q(visits__concept__icontains=name)
        clients = clients.filter(q_services).distinct()

    # Filtro por producto (ahora múltiple)
    product_ids = request.GET.getlist('product')
    if product_ids and 'all' not in product_ids:
        product_names = list(Product.objects.filter(id__in=product_ids).values_list('name', flat=True))
        q_products = Q()
        for name in product_names:
            q_products |= Q(sales__concept__icontains=name)
        clients = clients.filter(q_products).distinct()

    # Filtro por grupos (nuevo - múltiple)
    group_ids = request.GET.getlist('group')
    if group_ids and 'all' not in group_ids:
        clients = clients.filter(groups__id__in=group_ids).distinct()

    # Filtro por etiquetas/tags (múltiple - ya existía)
    selected_tags = request.GET.getlist('tags')
    if selected_tags and 'all' not in selected_tags:
        clients = clients.filter(tags__id__in=selected_tags).distinct()

    # Filtro por origen de alta (extra_data.created_from) - múltiple
    created_from_list = request.GET.getlist('created_from')
    if created_from_list and 'all' not in created_from_list:
        clients = clients.filter(extra_data__created_from__in=created_from_list)

    # Filtro por género - múltiple
    genders = request.GET.getlist('gender')
    if genders and 'all' not in genders:
        clients = clients.filter(gender__in=genders)

    # Filtro por estado - múltiple
    statuses = request.GET.getlist('status')
    if statuses and 'all' not in statuses:
        clients = clients.filter(status__in=statuses)

    # Filtro por edad (rango)
    age_min = request.GET.get('age_min')
    age_max = request.GET.get('age_max')
    from datetime import date
    today = date.today()
    if age_min:
        try:
            min_birth = today.replace(year=today.year - int(age_min))
            clients = clients.filter(birth_date__lte=min_birth)
        except Exception:
            pass
    if age_max:
        try:
            max_birth = today.replace(year=today.year - int(age_max) - 1)
            clients = clients.filter(birth_date__gte=max_birth)
        except Exception:
            pass

    for field in custom_fields:
        selected_value = request.GET.get(f"cf_{field.slug}")
        field.selected_value = selected_value or ''
        if selected_value:
            if field.field_type == ClientField.FieldType.TOGGLE:
                selected_bool = selected_value.lower() in ["1", "true", "yes", "on"]
                clients = clients.filter(**{f"extra_data__{field.slug}": selected_bool})
            else:
                clients = clients.filter(**{f"extra_data__{field.slug}": selected_value})

    date_start = request.GET.get('date_start')
    date_end = request.GET.get('date_end')
    if date_start:
        clients = clients.filter(created_at__date__gte=date_start)
    if date_end:
        clients = clients.filter(created_at__date__lte=date_end)

    # Filtros de Documentos
    document_template_id = request.GET.get('document_template')
    document_status = request.GET.get('document_status')

    if document_template_id and document_template_id != 'all':
        if document_status == 'signed':
            clients = clients.filter(
                documents__template_id=document_template_id,
                documents__status='SIGNED'
            ).distinct()
        elif document_status == 'pending':
            clients = clients.filter(
                documents__template_id=document_template_id,
                documents__status='PENDING'
            ).distinct()
        elif document_status == 'not_sent':
            clients = clients.exclude(
                documents__template_id=document_template_id
            )
        elif document_status == 'sent':
            clients = clients.filter(documents__template_id=document_template_id).distinct()

    # Obtener grupos para el contexto
    groups = ClientGroup.objects.filter(gym=gym)

    return clients, gym, custom_fields, custom_field_options, membership_plans, services, products, document_templates, groups


@login_required
@require_gym_permission("clients.view")
def client_explorer(request):
    (
        clients, gym, custom_fields, custom_field_options,
        membership_plans, services, products, document_templates, groups
    ) = _get_filtered_clients(request)
    if clients is None:
        return render(request, "backoffice/error.html", {"message": "No hay gimnasio seleccionado"})

    total_count = clients.count()
    active_count = clients.filter(status='ACTIVE').count()
    tags = ClientTag.objects.filter(gym=gym)

    clients = list(clients)
    for client in clients:
        values = {}
        if isinstance(client.extra_data, dict):
            for field in custom_fields:
                raw_value = client.extra_data.get(field.slug)
                if raw_value is not None and raw_value != "":
                    if field.field_type == ClientField.FieldType.TOGGLE:
                        values[field.slug] = "Sí" if raw_value else "No"
                    else:
                        values[field.slug] = custom_field_options.get(field.slug, {}).get(raw_value, raw_value)
        client.custom_field_values = values

    # Get filter values for context (ahora múltiples)
    q = request.GET.get('q')
    selected_statuses = request.GET.getlist('status')
    date_start = request.GET.get('date_start')
    date_end = request.GET.get('date_end')
    selected_tags = request.GET.getlist('tags')
    company = request.GET.get('company')
    selected_plans = request.GET.getlist('membership_plan')
    selected_services = request.GET.getlist('service')
    selected_products = request.GET.getlist('product')
    selected_groups = request.GET.getlist('group')
    selected_created_from = request.GET.getlist('created_from')
    selected_genders = request.GET.getlist('gender')
    age_min = request.GET.get('age_min', '')
    age_max = request.GET.get('age_max', '')
    document_template_id = request.GET.get('document_template', 'all')
    document_status = request.GET.get('document_status', 'all')

    context = {
        'clients': clients[:100],
        'total_count': total_count,
        'active_count': active_count,
        'tags': tags,
        'groups': groups,
        'custom_fields': custom_fields,
        'membership_plans': membership_plans,
        'services': services,
        'products': products,
        'document_templates': document_templates,
        'filters': {
            'q': q or '',
            'statuses': selected_statuses if selected_statuses else [],
            'date_start': date_start or '',
            'date_end': date_end or '',
            'tags': [int(t) for t in selected_tags] if selected_tags else [],
            'groups': [int(g) for g in selected_groups] if selected_groups else [],
            'company': company or 'all',
            'membership_plans': [int(p) for p in selected_plans] if selected_plans else [],
            'services': [int(s) for s in selected_services] if selected_services else [],
            'products': [int(p) for p in selected_products] if selected_products else [],
            'created_from': selected_created_from if selected_created_from else [],
            'genders': selected_genders if selected_genders else [],
            'age_min': age_min,
            'age_max': age_max,
            'document_template': document_template_id,
            'document_status': document_status,
        }
    }
    return render(request, "reporting/explorer.html", context)


@login_required
@require_gym_permission("clients.view")
def export_clients_csv(request):
    """Export filtered clients to CSV."""
    result = _get_filtered_clients(request)
    clients = result[0]
    gym = result[1]
    custom_fields = result[2]
    custom_field_options = result[3]
    if clients is None:
        return HttpResponse("No gym selected", status=400)
    
    response = HttpResponse(content_type='text/csv; charset=utf-8')
    response['Content-Disposition'] = f'attachment; filename="clientes_{gym.name}_{date.today()}.csv"'
    response.write('\ufeff')  # BOM for Excel UTF-8 compatibility
    
    writer = csv.writer(response)
    header = ['Nombre', 'Apellido', 'Email', 'Teléfono', 'Estado', 'Alta', 'Gasto Total', 'Empresa']
    header.extend([field.name for field in custom_fields])
    writer.writerow(header)
    
    for client in clients:
        values = {}
        if isinstance(client.extra_data, dict):
            for field in custom_fields:
                raw_value = client.extra_data.get(field.slug)
                if raw_value is not None and raw_value != "":
                    if field.field_type == ClientField.FieldType.TOGGLE:
                        values[field.slug] = "Sí" if raw_value else "No"
                    else:
                        values[field.slug] = custom_field_options.get(field.slug, {}).get(raw_value, raw_value)

        writer.writerow([
            client.first_name,
            client.last_name,
            client.email or '',
            client.phone_number or '',
            client.get_status_display(),
            client.created_at.strftime('%d/%m/%Y') if client.created_at else '',
            f"{client.total_spent:.2f}" if client.total_spent else '0.00',
            'Sí' if client.is_company_client else 'No',
            *[values.get(field.slug, '') for field in custom_fields],
        ])
    
    return response
