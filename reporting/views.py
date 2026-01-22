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

    # Filtro por tipo de cuota
    plan_id = request.GET.get('membership_plan')
    if plan_id and plan_id != 'all':
        clients = clients.filter(memberships__plan_id=plan_id).distinct()

    # Filtro por servicio
    service_id = request.GET.get('service')
    if service_id and service_id != 'all':
        clients = clients.filter(visits__concept__icontains=Service.objects.filter(id=service_id).first().name).distinct()

    # Filtro por producto
    product_id = request.GET.get('product')
    if product_id and product_id != 'all':
        clients = clients.filter(sales__concept__icontains=Product.objects.filter(id=product_id).first().name).distinct()

    # Filtro por origen de alta (extra_data.created_from)
    created_from = request.GET.get('created_from')
    if created_from and created_from != 'all':
        clients = clients.filter(extra_data__created_from=created_from)

    # Filtro por género
    gender = request.GET.get('gender')
    if gender and gender != 'all':
        clients = clients.filter(gender=gender)

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
    document_status = request.GET.get('document_status') # signed, pending, not_sent

    if document_template_id and document_template_id != 'all':
        if document_status == 'signed':
            # Clientes que TIENEN este documento FIRMADO
            clients = clients.filter(
                documents__template_id=document_template_id,
                documents__status='SIGNED'
            ).distinct()
        elif document_status == 'pending':
            # Clientes que TIENEN este documento PENDIENTE
            clients = clients.filter(
                documents__template_id=document_template_id,
                documents__status='PENDING'
            ).distinct()
        elif document_status == 'not_sent':
            # Clientes que NO tienen este documento (o no lo tienen en estado PENDING/SIGNED)
            # Usamos exclude para sacar a los que SI lo tienen
            clients = clients.exclude(
                documents__template_id=document_template_id
            )
        else:
            # Solo filtrar por clientes que tengan el documento asignado (cualquier estado)
            if document_status == 'sent':
                clients = clients.filter(documents__template_id=document_template_id).distinct()

    return clients, gym, custom_fields, custom_field_options, membership_plans, services, products, document_templates

@login_required
@require_gym_permission("clients.view")
def client_explorer(request):
    (
        clients, gym, custom_fields, custom_field_options,
        membership_plans, services, products, document_templates
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

    # Get filter values for context
    q = request.GET.get('q')
    status = request.GET.get('status')
    date_start = request.GET.get('date_start')
    date_end = request.GET.get('date_end')
    selected_tags = request.GET.getlist('tags')
    company = request.GET.get('company')
    # Nuevos filtros
    plan_id = request.GET.get('membership_plan', 'all')
    service_id = request.GET.get('service', 'all')
    product_id = request.GET.get('product', 'all')
    created_from = request.GET.get('created_from', 'all')
    gender = request.GET.get('gender', 'all')
    age_min = request.GET.get('age_min', '')
    age_max = request.GET.get('age_max', '')
    # Filtros Documentos
    document_template_id = request.GET.get('document_template', 'all')
    document_status = request.GET.get('document_status', 'all')

    context = {
        'clients': clients[:100],
        'total_count': total_count,
        'active_count': active_count,
        'tags': tags,
        'custom_fields': custom_fields,
        'membership_plans': membership_plans,
        'services': services,
        'products': products,
        'document_templates': document_templates,
        'filters': {
            'q': q or '',
            'status': status or 'all',
            'date_start': date_start or '',
            'date_end': date_end or '',
            'selected_tags': [int(t) for t in selected_tags],
            'company': company or 'all',
            'membership_plan': plan_id,
            'service': service_id,
            'product': product_id,
            'created_from': created_from,
            'gender': gender,
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
    clients, gym, custom_fields, custom_field_options = _get_filtered_clients(request)
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
