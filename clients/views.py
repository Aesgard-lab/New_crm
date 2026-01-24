from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.core.paginator import Paginator
from django.db.models import Q
from django.http import JsonResponse
from django.shortcuts import get_object_or_404, redirect, render
from django.views.decorators.http import require_POST
from django.utils import timezone
from django.utils.text import slugify

from accounts.decorators import require_gym_permission
from organizations.models import Gym
from .forms import ClientDocumentForm, ClientFieldForm, ClientForm, ClientGroupForm, ClientNoteForm, ClientTagForm
from .models import Client, ClientDocument, ClientField, ClientFieldOption, ClientGroup, ClientNote, ClientTag
from routines.models import WorkoutRoutine
from clients.utils.duplicate_detection import find_potential_duplicates


@login_required
@require_gym_permission("clients.change")
def merge_clients_wizard(request, c1_id, c2_id):
    # SECURITY FIX: Validate both clients belong to the current gym
    gym = request.gym
    c1 = get_object_or_404(Client, id=c1_id, gym=gym)
    c2 = get_object_or_404(Client, id=c2_id, gym=gym)
    conflict_warning = None
    # Comprobar conflictos de membresía activa
    c1_active_memberships = list(c1.memberships.filter(status="ACTIVE"))
    c2_active_memberships = list(c2.memberships.filter(status="ACTIVE"))
    if c1_active_memberships and c2_active_memberships:
        conflict_warning = "Ambos clientes tienen membresías activas. Revisa manualmente tras la fusión."

    if request.method == "POST":
        # Elegir qué datos conservar
        first_name = c1.first_name if request.POST.get("first_name") == "c1" else c2.first_name
        last_name = c1.last_name if request.POST.get("last_name") == "c1" else c2.last_name
        email = c1.email if request.POST.get("email") == "c1" else c2.email
        phone = c1.phone if request.POST.get("phone") == "c1" else c2.phone
        # Fusionar: c1 será el principal, c2 se borra
        c1.first_name = first_name
        c1.last_name = last_name
        c1.email = email
        c1.phone = phone
        # Unificar historiales y relaciones
        # Notas
        for note in c2.notes.all():
            note.client = c1
            note.save()
        # Documentos
        for doc in c2.documents.all():
            doc.client = c1
            doc.save()
        # Membresías
        for memb in c2.memberships.all():
            memb.client = c1
            memb.save()
        # Visitas
        for visit in c2.visits.all():
            visit.client = c1
            visit.save()
        # Ventas
        for sale in c2.sales.all():
            sale.client = c1
            sale.save()
        # Grupos y etiquetas (ManyToMany)
        for group in c2.groups.all():
            c1.groups.add(group)
        for tag in c2.tags.all():
            c1.tags.add(tag)
        # ChatRoom (si existe en c2 y no en c1)
        if hasattr(c2, "chat_room") and not hasattr(c1, "chat_room"):
            c2.chat_room.client = c1
            c2.chat_room.save()
        # Pedidos/Ventas (Order)
        try:
            from sales.models import Order
            for order in Order.objects.filter(client=c2):
                order.client = c1
                order.save()
        except Exception:
            pass
        # TODO: Unificar otros historiales si aplica (pagos, reservas, etc.)
        c1.save()
        c2.delete()
        messages.success(request, "Fichas fusionadas correctamente.")
        return redirect("clients_duplicates")
    return render(request, "clients/merge_wizard.html", {"c1": c1, "c2": c2, "conflict_warning": conflict_warning})


@login_required
@require_gym_permission("clients.view")
def clients_duplicates(request):
    # Opcional: filtrar solo por el gimnasio actual si aplica multi-gym
    duplicates = find_potential_duplicates()
    return render(request, "clients/duplicates.html", {"duplicates": duplicates})


@login_required
@require_gym_permission("clients.view")
def clients_list(request):
    gym = getattr(request, "gym", None)
    if not gym:
        gym_id = request.session.get("current_gym_id")
        gym = Gym.objects.filter(id=gym_id).first()
        if not gym:
            return redirect("home")

    clients = Client.objects.filter(gym=gym).prefetch_related("tags")

    query = request.GET.get("q", "").strip()
    if query:
        clients = clients.filter(
            Q(first_name__icontains=query)
            | Q(last_name__icontains=query)
            | Q(email__icontains=query)
            | Q(phone_number__icontains=query)
        )

    status = request.GET.get("status", "all")
    if status and status != "all":
        clients = clients.filter(status=status)

    selected_tags = request.GET.getlist("tags")
    if selected_tags:
        clients = clients.filter(tags__id__in=selected_tags)

    company = request.GET.get("company", "all")
    if company == "company":
        clients = clients.filter(is_company_client=True)
    elif company == "individual":
        clients = clients.filter(is_company_client=False)

    # Filtro por pasarela de pago
    gateway = request.GET.get("gateway", "all")
    if gateway == "stripe":
        clients = clients.filter(Q(preferred_gateway='STRIPE') | Q(stripe_customer_id__isnull=False))
    elif gateway == "redsys":
        clients = clients.filter(Q(preferred_gateway='REDSYS') | Q(redsys_tokens__isnull=False)).distinct()
    elif gateway == "auto":
        clients = clients.filter(preferred_gateway='AUTO', stripe_customer_id__isnull=True).exclude(redsys_tokens__isnull=False)

    custom_fields = list(
        ClientField.objects.filter(gym=gym, is_active=True)
        .prefetch_related("options")
        .order_by("name")
    )
    custom_field_filters = {}
    for field in custom_fields:
        selected_value = request.GET.get(f"cf_{field.slug}")
        if selected_value:
            custom_field_filters[field.slug] = selected_value
            if field.field_type == ClientField.FieldType.TOGGLE:
                selected_bool = selected_value.lower() in ["1", "true", "yes", "on"]
                clients = clients.filter(**{f"extra_data__{field.slug}": selected_bool})
            else:
                clients = clients.filter(**{f"extra_data__{field.slug}": selected_value})
        field.selected_value = selected_value or ""

    clients = clients.order_by("-created_at").distinct()

    custom_field_options = {
        field.slug: ({True: "Sí", False: "No"} if field.field_type == ClientField.FieldType.TOGGLE else {opt.value: opt.label for opt in field.options.all()})
        for field in custom_fields
    }

    # Paginación - 50 clientes por página
    paginator = Paginator(clients, 50)
    page_number = request.GET.get('page', 1)
    page_obj = paginator.get_page(page_number)
    
    clients_page = list(page_obj.object_list)
    custom_field_values = {}
    for client in clients_page:
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
        custom_field_values[client.id] = values

    from memberships.models import MembershipPlan
    from services.models import Service
    from products.models import Product

    membership_plans = MembershipPlan.objects.filter(gym=gym, is_active=True).order_by('name')
    services = Service.objects.filter(gym=gym, is_active=True).order_by('name')
    products = Product.objects.filter(gym=gym, is_active=True).order_by('name')

    context = {
        "clients": clients_page,
        "page_obj": page_obj,
        "paginator": paginator,
        "tags": gym.client_tags.all(),
        "custom_fields": custom_fields,
        "custom_field_options": custom_field_options,
        "custom_field_values": custom_field_values,
        "membership_plans": membership_plans,
        "services": services,
        "products": products,
        "filters": {
            "q": query,
            "status": status or "all",
            "selected_tags": [int(t) for t in selected_tags] if selected_tags else [],
            "company": company or "all",
            "gateway": gateway or "all",
            "custom_field_filters": custom_field_filters,
            "membership_plan": request.GET.get('membership_plan', 'all'),
            "service": request.GET.get('service', 'all'),
            "product": request.GET.get('product', 'all'),
            "created_from": request.GET.get('created_from', 'all'),
            "gender": request.GET.get('gender', 'all'),
            "age_min": request.GET.get('age_min', ''),
            "age_max": request.GET.get('age_max', ''),
        },
    }
    return render(request, "backoffice/clients/list.html", context)

@login_required
@require_gym_permission("clients.view")
def client_detail(request, client_id):
    gym = getattr(request, "gym", None)
    if not gym:
        return redirect("home")

    # Seguridad: Solo clientes del gym actual
    client = get_object_or_404(
        Client.objects.prefetch_related(
            "tags",
            "notes__author",
            "memberships",
            "visits",
            "orders__items",
            "orders__payments__payment_method",
            "documents",
        ),
        id=client_id,
        gym=gym,
    )

    # Stripe Payment Methods
    from finance.stripe_utils import list_payment_methods
    
    # Stripe Context
    finance_settings = getattr(client.gym, 'finance_settings', None)
    stripe_public_key = finance_settings.stripe_public_key if finance_settings else ''
    
    # Redsys Context
    redsys_enabled = bool(finance_settings and finance_settings.redsys_merchant_code and finance_settings.redsys_secret_key)
    
    # Pay methods
    try:
        payment_methods = list_payment_methods(client)
    except:
        payment_methods = []
        
    # Helper lists (could be filtered/sorted if needed)
    memberships = client.memberships.prefetch_related('pauses').order_by("-start_date")
    visits = client.visits.order_by("-date")
    notes = client.notes.order_by("-created_at")
    note_form = ClientNoteForm()
    document_form = ClientDocumentForm()
    
    # Get popup alerts
    popup_alerts = client.notes.filter(is_popup=True).order_by("-created_at")
    
    # Routines Context
    routine_templates = WorkoutRoutine.objects.filter(gym=client.gym, is_template=True).order_by('name')
    client_routines = client.routines.filter(is_active=True).select_related('routine').order_by('-start_date')

    custom_fields = list(
        ClientField.objects.filter(gym=gym, is_active=True)
        .prefetch_related("options")
        .order_by("name")
    )
    custom_field_options = {
        field.slug: ({True: "Sí", False: "No"} if field.field_type == ClientField.FieldType.TOGGLE else {opt.value: opt.label for opt in field.options.all()})
        for field in custom_fields
    }
    custom_field_values = {}
    for field in custom_fields:
        value = ""
        if isinstance(client.extra_data, dict):
            raw_value = client.extra_data.get(field.slug)
            if raw_value is not None and raw_value != "":
                if field.field_type == ClientField.FieldType.TOGGLE:
                    value = "Sí" if raw_value else "No"
                else:
                    value = custom_field_options.get(field.slug, {}).get(raw_value, raw_value)
        custom_field_values[field.slug] = value
        field.display_value = value

    # Document Templates for selector
    document_templates = DocumentTemplate.objects.filter(gym=gym, is_active=True).order_by('name')

    # Access Control - Historial de accesos físicos (entrada/salida)
    try:
        from access_control.models import AccessLog, ClientAccessCredential
        access_logs = AccessLog.objects.filter(
            client=client
        ).select_related('device', 'device__zone').order_by('-timestamp')[:50]
        
        # Credenciales de acceso del cliente
        access_credentials = ClientAccessCredential.objects.filter(
            client=client, is_active=True
        ).order_by('-created_at')
    except:
        access_logs = []
        access_credentials = []

    # Taquillas asignadas al cliente
    try:
        from lockers.models import LockerAssignment
        locker_assignments = LockerAssignment.objects.filter(
            client=client,
            status='ACTIVE'
        ).select_related('locker', 'locker__zone').order_by('-start_date')
    except:
        locker_assignments = []

    context = {
        'client': client,
        'title': f'{client.first_name} {client.last_name}',
        'active_tab': 'clients',
        'notes': notes,
        'note_form': note_form,
        'popup_alerts': popup_alerts,
        'memberships': memberships,
        'visits': visits,
        'document_form': document_form,
        'document_templates': document_templates,
        'stripe_public_key': stripe_public_key,
        'payment_methods': payment_methods,
        'redsys_enabled': redsys_enabled,
        'redsys_tokens': client.redsys_tokens.all(),
        'routine_templates': routine_templates,
        'client_routines': client_routines,
        'custom_fields': custom_fields,
        'custom_field_options': custom_field_options,
        'custom_field_values': custom_field_values,
        'access_logs': access_logs,
        'access_credentials': access_credentials,
        'locker_assignments': locker_assignments,
    }
    return render(request, "backoffice/clients/detail.html", context)


@login_required
@require_gym_permission("clients.change")
def client_get_stripe_setup(request, client_id):
    """
    Returns a SetupIntent client_secret to link a new card.
    """
    gym = getattr(request, "gym", None)
    client = get_object_or_404(Client, id=client_id, gym=gym)
    
    try:
        from finance.stripe_utils import create_setup_intent
        client_secret = create_setup_intent(client)
        return JsonResponse({'client_secret': client_secret})
    except Exception as e:
        return JsonResponse({'error': str(e)}, status=400)


@login_required
@require_gym_permission("clients.change")
@require_POST
def client_update_preferred_gateway(request, client_id):
    """
    Updates the client's preferred payment gateway.
    """
    gym = getattr(request, "gym", None)
    client = get_object_or_404(Client, id=client_id, gym=gym)
    
    import json
    try:
        data = json.loads(request.body)
        gateway = data.get('gateway', 'AUTO')
    except:
        gateway = request.POST.get('gateway', 'AUTO')
    
    if gateway in ['AUTO', 'STRIPE', 'REDSYS']:
        client.preferred_gateway = gateway
        client.save(update_fields=['preferred_gateway'])
        return JsonResponse({'success': True, 'gateway': gateway})
    else:
        return JsonResponse({'error': 'Invalid gateway'}, status=400)


@login_required
@require_gym_permission("clients.change")
def client_edit(request, client_id):
    gym = getattr(request, "gym", None)
    if not gym:
        return redirect("home")

    # Seguridad: Solo clientes del gym actual
    client = get_object_or_404(Client, id=client_id, gym=gym)

    if request.method == "POST":
        form = ClientForm(request.POST, request.FILES, instance=client, gym=gym)
        if form.is_valid():
            form.save()
            return redirect("client_detail", client_id=client.id)
    else:
        form = ClientForm(instance=client, gym=gym)

    return render(request, "backoffice/clients/form.html", {
        "form": form, 
        "title": f"Editar {client.first_name}"
    })

@login_required
@require_POST
def client_add_note(request, client_id):
    gym = getattr(request, "gym", None)
    client = get_object_or_404(Client, id=client_id, gym=gym)
    
    form = ClientNoteForm(request.POST)
    if form.is_valid():
        note = form.save(commit=False)
        note.client = client
        note.author = request.user
        note.save()
    
    return redirect("client_detail", client_id=client.id)


@login_required
def client_edit_note(request, note_id):
    gym = getattr(request, "gym", None)
    # Verify note belongs to a client in the current gym
    note = get_object_or_404(ClientNote, id=note_id, client__gym=gym)
    
    # Optional: Check author permissions
    
    if request.method == "POST":
        form = ClientNoteForm(request.POST, instance=note)
        if form.is_valid():
            form.save()
            return redirect("client_detail", client_id=note.client.id)
    else:
        form = ClientNoteForm(instance=note)

    return render(request, "backoffice/clients/note_form.html", {
        "form": form,
        "client_id": note.client.id
    })


@login_required
@require_POST
def client_delete_note(request, note_id):
    gym = getattr(request, "gym", None)
    # Verify note belongs to a client in the current gym
    note = get_object_or_404(ClientNote, id=note_id, client__gym=gym)
    
    # Optional: Check if user is author or has delete permission
    note.delete()
    return redirect("client_detail", client_id=note.client.id)


@login_required
@require_POST
def client_add_document(request, client_id):
    gym = getattr(request, "gym", None)
    client = get_object_or_404(Client, id=client_id, gym=gym)
    
    form = ClientDocumentForm(request.POST, request.FILES)
    if form.is_valid():
        doc = form.save(commit=False)
        doc.client = client
        doc.created_by = request.user
        doc.sent_at = timezone.now()  # Marcar como enviado al crearlo
        doc.status = 'PENDING' if doc.requires_signature else 'SIGNED'
        doc.save()
        messages.success(request, f"✅ Documento '{doc.name}' enviado correctamente.")
    else:
        for error in form.errors:
            messages.error(request, f"Error: {form.errors[error]}")
    
    return redirect("client_detail", client_id=client.id)


@login_required
@require_gym_permission("clients.create")
def client_create(request):
    gym = getattr(request, "gym", None)
    if not gym:
        return redirect("home")

    if request.method == "POST":
        form = ClientForm(request.POST, request.FILES, gym=gym)
        if form.is_valid():
            client = form.save(commit=False)
            client.gym = gym
            client.save()
            form.save_m2m()  # Guardar tags/groups si los hubiera
            return redirect("clients")
    else:
        form = ClientForm(gym=gym)

    return render(request, "backoffice/clients/form.html", {"form": form, "title": "Nuevo Cliente"})


@login_required
@require_gym_permission("clients.change")
def client_settings(request):
    gym = getattr(request, "gym", None)
    if not gym:
        return redirect("home")

    fields = list(
        ClientField.objects.filter(gym=gym)
        .prefetch_related("options")
        .order_by("name")
    )
    field_form = ClientFieldForm()
    group_form = ClientGroupForm()
    tag_form = ClientTagForm(initial={"color": "#94a3b8"})

    if request.method == "POST":
        # Handle booking settings toggle
        if request.POST.get("form_type") == "booking_settings":
            gym.allow_booking_with_pending_payment = request.POST.get("allow_booking_with_pending_payment") == "on"
            gym.save(update_fields=["allow_booking_with_pending_payment"])
            messages.success(request, "Configuración de reservas actualizada.")
            return redirect("client_settings")

        delete_id = request.POST.get("delete_field")
        if delete_id:
            field = get_object_or_404(ClientField, id=delete_id, gym=gym)
            field.delete()
            messages.success(request, f"Campo '{field.name}' eliminado.")
            return redirect("client_settings")

        delete_group_id = request.POST.get("delete_group")
        if delete_group_id:
            group = get_object_or_404(ClientGroup, id=delete_group_id, gym=gym)
            group.delete()
            messages.success(request, f"Grupo '{group.name}' eliminado.")
            return redirect("client_settings")

        delete_tag_id = request.POST.get("delete_tag")
        if delete_tag_id:
            tag = get_object_or_404(ClientTag, id=delete_tag_id, gym=gym)
            tag.delete()
            messages.success(request, f"Etiqueta '{tag.name}' eliminada.")
            return redirect("client_settings")

        if request.POST.get("form_type") == "field":
            field_form = ClientFieldForm(request.POST)
            if field_form.is_valid():
                field = field_form.save(commit=False)
                field.gym = gym
                field.save()

                if field.field_type == ClientField.FieldType.SELECT:
                    options_raw = field_form.cleaned_data.get("options_raw", "")
                    seen_values = set()
                    for order, line in enumerate(options_raw.splitlines()):
                        label = line.strip()
                        if not label:
                            continue
                        value = slugify(label) or slugify(f"{label}-{order}")
                        if value in seen_values:
                            continue
                        seen_values.add(value)
                        ClientFieldOption.objects.create(
                            field=field,
                            label=label,
                            value=value,
                            order=order,
                        )

                messages.success(request, "Campo personalizado creado correctamente.")
                return redirect("client_settings")
            else:
                messages.error(request, "No se pudo crear el campo. Revisa los datos.")

        if request.POST.get("form_type") == "group":
            group_form = ClientGroupForm(request.POST)
            if group_form.is_valid():
                group = group_form.save(commit=False)
                group.gym = gym
                group.save()
                messages.success(request, "Grupo creado.")
                return redirect("client_settings")
            else:
                messages.error(request, "No se pudo crear el grupo. Revisa los datos.")

        if request.POST.get("form_type") == "tag":
            tag_form = ClientTagForm(request.POST)
            if tag_form.is_valid():
                tag = tag_form.save(commit=False)
                tag.gym = gym
                tag.save()
                messages.success(request, "Etiqueta creada.")
                return redirect("client_settings")
            else:
                messages.error(request, "No se pudo crear la etiqueta. Revisa los datos.")

    context = {
        "fields": fields,
        "field_form": field_form,
        "group_form": group_form,
        "tag_form": tag_form,
        "groups": ClientGroup.objects.filter(gym=gym).order_by("name"),
        "tags": ClientTag.objects.filter(gym=gym).order_by("name"),
        "gym": gym,
    }
    return render(request, "backoffice/clients/settings.html", context)

# ===========================
# IMPORTACIÓN DE CLIENTES CSV
# ===========================

@login_required
@require_gym_permission("clients.add")
def client_import(request):
    """Vista para importar clientes desde CSV"""
    from .forms import ClientImportForm
    from .import_service import ClientImportService
    
    gym = request.gym
    results = None
    form = ClientImportForm()
    
    if request.method == "POST":
        form = ClientImportForm(request.POST, request.FILES)
        
        if form.is_valid():
            csv_file = request.FILES['csv_file']
            update_existing = form.cleaned_data['update_existing']
            skip_errors = form.cleaned_data['skip_errors']
            
            # Procesar importación
            service = ClientImportService(gym)
            results = service.import_from_csv(
                csv_file,
                update_existing=update_existing,
                skip_errors=skip_errors
            )
    
    context = {
        "form": form,
        "results": results,
        "title": "Importar Clientes",
    }
    return render(request, "backoffice/clients/import.html", context)


# ===========================
# EXPORTACIÓN DE CLIENTES
# ===========================

@login_required
@require_gym_permission("clients.view")
def client_export_excel(request):
    """Exporta listado de clientes a Excel"""
    from .export_service import ClientExportService
    from django.http import HttpResponse
    from datetime import datetime
    
    gym = request.gym
    clients = Client.objects.filter(gym=gym).order_by('-created_at')
    
    # Generar Excel
    excel_file = ClientExportService.export_to_excel(clients, gym.name)
    
    # Preparar respuesta
    response = HttpResponse(
        excel_file.read(),
        content_type='application/vnd.openxmlformats-officedocument.spreadsheetml.sheet'
    )
    response['Content-Disposition'] = f'attachment; filename="clientes_{gym.name}_{datetime.now().strftime("%Y%m%d")}.xlsx"'
    
    return response


import json
from datetime import datetime

@login_required
@require_POST
def api_edit_membership(request):
    """API para editar una membresía del cliente"""
    try:
        data = json.loads(request.body)
        membership_id = data.get('membership_id')
        start_date = data.get('start_date')
        end_date = data.get('end_date')
        price = data.get('price')
        status = data.get('status')
        is_recurring = data.get('is_recurring', True)
        sessions_total = data.get('sessions_total')
        sessions_used = data.get('sessions_used', 0)
        next_billing_date = data.get('next_billing_date')
        access_rules = data.get('access_rules', [])
        
        if not all([membership_id, start_date, price, status]):
            return JsonResponse({'error': 'Faltan datos requeridos'}, status=400)
        
        # Obtener la membresía
        from clients.models import ClientMembership, ClientMembershipAccessRule
        membership = get_object_or_404(ClientMembership, id=membership_id, client__gym=request.gym)
        
        # Convertir fechas
        try:
            start_date_obj = datetime.strptime(start_date, '%Y-%m-%d').date()
            end_date_obj = datetime.strptime(end_date, '%Y-%m-%d').date() if end_date else None
            next_billing_date_obj = datetime.strptime(next_billing_date, '%Y-%m-%d').date() if next_billing_date else None
        except ValueError:
            return JsonResponse({'error': 'Formato de fecha inválido'}, status=400)
        
        # Validar
        if end_date_obj and end_date_obj < start_date_obj:
            return JsonResponse({'error': 'La fecha de fin debe ser posterior a la de inicio'}, status=400)
        
        # Actualizar campos básicos
        membership.start_date = start_date_obj
        membership.end_date = end_date_obj
        membership.price = float(price)
        membership.status = status
        
        # Actualizar campos adicionales
        membership.is_recurring = is_recurring
        membership.sessions_total = int(sessions_total) if sessions_total is not None else None
        membership.sessions_used = int(sessions_used) if sessions_used is not None else 0
        membership.next_billing_date = next_billing_date_obj
        
        membership.save()
        
        # Actualizar reglas de acceso
        # Obtener IDs de reglas existentes para saber cuáles eliminar
        existing_rule_ids = set(membership.access_rules.values_list('id', flat=True))
        updated_rule_ids = set()
        
        for rule_data in access_rules:
            rule_id = rule_data.get('id')
            
            # Verificar que al menos una categoría o entidad esté seleccionada
            has_target = any([
                rule_data.get('activity_category_id'),
                rule_data.get('activity_id'),
                rule_data.get('service_category_id'),
                rule_data.get('service_id'),
            ])
            
            if not has_target:
                continue  # Ignorar reglas sin objetivo
            
            if rule_id and rule_id in existing_rule_ids:
                # Actualizar regla existente
                rule = ClientMembershipAccessRule.objects.get(id=rule_id, membership=membership)
                updated_rule_ids.add(rule_id)
            else:
                # Crear nueva regla
                rule = ClientMembershipAccessRule(membership=membership)
            
            rule.activity_category_id = rule_data.get('activity_category_id') or None
            rule.activity_id = rule_data.get('activity_id') or None
            rule.service_category_id = rule_data.get('service_category_id') or None
            rule.service_id = rule_data.get('service_id') or None
            rule.quantity = int(rule_data.get('quantity', 0))
            rule.quantity_used = int(rule_data.get('quantity_used', 0))
            rule.period = rule_data.get('period', 'PER_CYCLE')
            rule.save()
            
            if rule.id:
                updated_rule_ids.add(rule.id)
        
        # Eliminar reglas que ya no están
        rules_to_delete = existing_rule_ids - updated_rule_ids
        ClientMembershipAccessRule.objects.filter(id__in=rules_to_delete).delete()
        
        return JsonResponse({
            'success': True,
            'message': 'Membresía actualizada correctamente'
        })
        
    except Exception as e:
        return JsonResponse({'error': str(e)}, status=500)


@login_required
def api_get_membership_details(request, membership_id):
    """API para obtener detalles de una membresía incluyendo reglas de acceso"""
    from clients.models import ClientMembership, ClientMembershipAccessRule
    from activities.models import Activity, ActivityCategory
    from services.models import Service, ServiceCategory
    
    membership = get_object_or_404(ClientMembership, id=membership_id, client__gym=request.gym)
    
    # Obtener todas las categorías y entidades del gimnasio
    activity_categories = list(ActivityCategory.objects.filter(gym=request.gym).values('id', 'name'))
    activities = list(Activity.objects.filter(gym=request.gym).values('id', 'name', 'category_id'))
    service_categories = list(ServiceCategory.objects.filter(gym=request.gym).values('id', 'name'))
    services = list(Service.objects.filter(gym=request.gym).values('id', 'name', 'category_id'))
    
    # Obtener las reglas de acceso de esta membresía
    access_rules = []
    for rule in membership.access_rules.all():
        access_rules.append({
            'id': rule.id,
            'activity_category_id': rule.activity_category_id,
            'activity_id': rule.activity_id,
            'service_category_id': rule.service_category_id,
            'service_id': rule.service_id,
            'quantity': rule.quantity,
            'quantity_used': rule.quantity_used,
            'period': rule.period,
        })
    
    return JsonResponse({
        'membership': {
            'id': membership.id,
            'name': membership.name,
            'start_date': membership.start_date.isoformat() if membership.start_date else None,
            'end_date': membership.end_date.isoformat() if membership.end_date else None,
            'price': float(membership.price),
            'status': membership.status,
            'is_recurring': membership.is_recurring,
            'sessions_total': membership.sessions_total,
            'sessions_used': membership.sessions_used,
            'next_billing_date': membership.next_billing_date.isoformat() if membership.next_billing_date else None,
        },
        'access_rules': access_rules,
        'activity_categories': activity_categories,
        'activities': activities,
        'service_categories': service_categories,
        'services': services,
    })


@login_required
@require_gym_permission("clients.view")
def client_export_pdf(request):
    """Exporta listado de clientes a PDF"""
    from .export_service import ClientExportService
    from django.http import HttpResponse
    from datetime import datetime
    
    gym = request.gym
    clients = Client.objects.filter(gym=gym).order_by('-created_at')
    
    # Generar PDF
    pdf_file = ClientExportService.export_to_pdf(clients, gym.name)
    
    # Preparar respuesta
    response = HttpResponse(pdf_file.read(), content_type='application/pdf')
    response['Content-Disposition'] = f'attachment; filename="clientes_{gym.name}_{datetime.now().strftime("%Y%m%d")}.pdf"'
    
    return response


@login_required
@require_gym_permission("clients.view")
@require_POST
def client_toggle_email_notifications(request, client_id):
    """Toggle email notifications preference for a client (AJAX endpoint)"""
    gym = request.gym
    client = get_object_or_404(Client, id=client_id, gym=gym)
    
    # Toggle the preference
    client.email_notifications_enabled = not client.email_notifications_enabled
    client.save()
    
    return JsonResponse({
        'success': True,
        'email_notifications_enabled': client.email_notifications_enabled,
        'message': 'Preferencias actualizadas correctamente'
    })


# ===========================
# PLANTILLAS DE DOCUMENTOS
# ===========================

from .models import DocumentTemplate
from .forms import DocumentTemplateForm

@login_required
@require_gym_permission("clients.change")
def document_template_list(request):
    """Listado de plantillas de documentos"""
    gym = getattr(request, "gym", None)
    if not gym:
        return redirect("home")
    
    templates = DocumentTemplate.objects.filter(gym=gym).order_by('name')
    
    context = {
        'templates': templates,
        'title': 'Plantillas de Documentos',
    }
    return render(request, "backoffice/settings/documents/list.html", context)


@login_required
@require_gym_permission("clients.change")
def document_template_create(request):
    """Crear nueva plantilla de documento"""
    gym = getattr(request, "gym", None)
    if not gym:
        return redirect("home")
    
    if request.method == "POST":
        form = DocumentTemplateForm(request.POST)
        if form.is_valid():
            template = form.save(commit=False)
            template.gym = gym
            template.created_by = request.user
            template.save()
            messages.success(request, f"✅ Plantilla '{template.name}' creada correctamente.")
            return redirect("document_template_list")
    else:
        form = DocumentTemplateForm()
    
    context = {
        'form': form,
        'title': 'Nueva Plantilla de Documento',
    }
    return render(request, "backoffice/settings/documents/form.html", context)


@login_required
@require_gym_permission("clients.change")
def document_template_edit(request, pk):
    """Editar plantilla de documento"""
    gym = getattr(request, "gym", None)
    if not gym:
        return redirect("home")
    
    template = get_object_or_404(DocumentTemplate, id=pk, gym=gym)
    
    if request.method == "POST":
        form = DocumentTemplateForm(request.POST, instance=template)
        if form.is_valid():
            form.save()
            messages.success(request, f"✅ Plantilla '{template.name}' actualizada.")
            return redirect("document_template_list")
    else:
        form = DocumentTemplateForm(instance=template)
    
    context = {
        'form': form,
        'template': template,
        'title': f'Editar: {template.name}',
    }
    return render(request, "backoffice/settings/documents/form.html", context)


@login_required
@require_gym_permission("clients.change")
@require_POST
def document_template_delete(request, pk):
    """Eliminar plantilla de documento"""
    gym = getattr(request, "gym", None)
    if not gym:
        return redirect("home")
    
    template = get_object_or_404(DocumentTemplate, id=pk, gym=gym)
    name = template.name
    template.delete()
    messages.success(request, f"Plantilla '{name}' eliminada.")
    return redirect("document_template_list")


# ===========================
# ENVÍO DE DOCUMENTOS A CLIENTES
# ===========================

@login_required
@require_gym_permission("clients.change")
@require_POST
def client_send_document(request, client_id):
    """Enviar documento a cliente desde plantilla"""
    gym = getattr(request, "gym", None)
    client = get_object_or_404(Client, id=client_id, gym=gym)
    
    template_id = request.POST.get('template_id')
    template = get_object_or_404(DocumentTemplate, id=template_id, gym=gym)
    
    # Procesar variables en el contenido
    content = template.content
    content = content.replace('{{client_name}}', f"{client.first_name} {client.last_name}")
    content = content.replace('{{client_dni}}', client.dni or "")
    content = content.replace('{{date}}', timezone.now().strftime('%d/%m/%Y'))
    content = content.replace('{{gym_name}}', gym.commercial_name or gym.name)
    
    # Crear documento para el cliente
    doc = ClientDocument.objects.create(
        client=client,
        template=template,
        name=template.name,
        document_type=template.document_type,
        content=content,
        requires_signature=template.requires_signature,
        status='PENDING' if template.requires_signature else 'DRAFT',
        sent_at=timezone.now(),
        created_by=request.user
    )
    
    messages.success(request, f"✅ Documento '{doc.name}' enviado al cliente.")
    return redirect("client_detail", client_id=client.id)


@login_required
@require_gym_permission("clients.change")
def client_sign_insitu(request, client_id, document_id):
    """Firma in-situ de documento (en tablet/PC del centro)"""
    from django.core.files.base import ContentFile
    import base64
    import uuid
    
    gym = getattr(request, "gym", None)
    client = get_object_or_404(Client, id=client_id, gym=gym)
    document = get_object_or_404(ClientDocument, id=document_id, client=client)
    
    if request.method == "POST":
        # Recibir firma en base64
        signature_data = request.POST.get('signature_image')
        
        if not signature_data:
            return JsonResponse({'error': 'Se requiere la firma'}, status=400)
        
        try:
            # Decode base64 image
            format_str, imgstr = signature_data.split(';base64,') 
            ext = format_str.split('/')[-1] 
            data = ContentFile(base64.b64decode(imgstr), name=f'{uuid.uuid4()}.{ext}')
            
            # Guardar firma
            document.signature_image = data
            document.status = 'SIGNED'
            document.is_signed = True
            document.signed_at = timezone.now()
            
            # Get IP
            x_forwarded_for = request.META.get('HTTP_X_FORWARDED_FOR')
            if x_forwarded_for:
                ip = x_forwarded_for.split(',')[0]
            else:
                ip = request.META.get('REMOTE_ADDR')
            document.signed_ip = ip
            
            document.save()
            
            return JsonResponse({
                'success': True,
                'message': 'Documento firmado correctamente',
                'signed_at': document.signed_at.isoformat()
            })
            
        except Exception as e:
            return JsonResponse({'error': f'Error procesando firma: {str(e)}'}, status=500)
    
    # GET: Mostrar modal/página de firma
    context = {
        'client': client,
        'document': document,
        'title': f'Firmar: {document.name}',
    }
    return render(request, "backoffice/clients/sign_insitu.html", context)


@login_required
@require_gym_permission("clients.change")
@require_POST  
def bulk_send_document(request):
    """Enviar documento a múltiples clientes"""
    gym = getattr(request, "gym", None)
    if not gym:
        return JsonResponse({'error': 'No hay gimnasio seleccionado'}, status=400)
    
    client_ids = request.POST.getlist('client_ids')
    template_id = request.POST.get('template_id')
    
    if not client_ids or not template_id:
        return JsonResponse({'error': 'Faltan parámetros'}, status=400)
    
    template = get_object_or_404(DocumentTemplate, id=template_id, gym=gym)
    
    created_count = 0
    skipped_count = 0
    
    for client_id in client_ids:
        try:
            client = Client.objects.get(id=client_id, gym=gym)
            
            # Verificar que no exista ya este documento pendiente
            existing = ClientDocument.objects.filter(
                client=client, 
                template=template,
                status__in=['PENDING', 'SIGNED']
            ).exists()
            
            if existing:
                skipped_count += 1
                continue
            
            # Procesar variables
            content = template.content
            content = content.replace('{{client_name}}', f"{client.first_name} {client.last_name}")
            content = content.replace('{{client_dni}}', client.dni or "")
            content = content.replace('{{date}}', timezone.now().strftime('%d/%m/%Y'))
            content = content.replace('{{gym_name}}', gym.commercial_name or gym.name)
            
            ClientDocument.objects.create(
                client=client,
                template=template,
                name=template.name,
                document_type=template.document_type,
                content=content,
                requires_signature=template.requires_signature,
                status='PENDING' if template.requires_signature else 'DRAFT',
                sent_at=timezone.now(),
                created_by=request.user
            )
            created_count += 1
            
        except Client.DoesNotExist:
            continue
    
    return JsonResponse({
        'success': True, 
        'created': created_count,
        'skipped': skipped_count,
        'message': f'Documento enviado a {created_count} clientes. {skipped_count} omitidos (ya tenían el documento).'
    })
