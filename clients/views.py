from django.shortcuts import render
from django.contrib.auth.decorators import login_required
from accounts.decorators import require_gym_permission
from organizations.models import Gym

@login_required
@require_gym_permission("clients.view")
def clients_list(request):
    gym_id = request.session.get("current_gym_id")
    
    # Obtener clientes del gym actual
    # Usamos prefetch_related para tags y groups para evitar N+1 queries
    clients = []
    if gym_id:
        gym = Gym.objects.filter(id=gym_id).first()
        if gym:
            clients = gym.clients.all().prefetch_related("tags")

    context = {
        "clients": clients,
    }
    return render(request, "backoffice/clients/list.html", context)


from django.shortcuts import redirect, get_object_or_404
from .forms import ClientForm, ClientNoteForm
from .models import Client

@login_required
@require_gym_permission("clients.view")
def client_detail(request, client_id):
    gym_id = request.session.get("current_gym_id")
    if not gym_id:
        return redirect("home")
    
    # Seguridad: Solo clientes del gym actual
    client = get_object_or_404(
        Client.objects.prefetch_related(
            "tags",
            "notes__author", 
            "memberships",
            "visits",
            "sales",
            "documents"
        ), 
        id=client_id, 
        gym_id=gym_id
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
    memberships = client.memberships.order_by("-start_date")
    visits = client.visits.order_by("-date")
    sales = client.sales.order_by("-date")
    notes = client.notes.order_by("-created_at")
    note_form = ClientNoteForm()
    document_form = ClientDocumentForm() # Assuming ClientDocumentForm is the correct class

    context = {
        'client': client,
        'title': f'{client.first_name} {client.last_name}',
        'active_tab': 'clients',
        'notes': notes,
        'note_form': note_form,
        'memberships': memberships,
        'visits': visits,
        'sales': sales, # Retained from original
        'document_form': document_form,
        'stripe_public_key': stripe_public_key,
        'payment_methods': payment_methods,
        'redsys_enabled': redsys_enabled,
        'redsys_tokens': client.redsys_tokens.all()
    }
    return render(request, "backoffice/clients/detail.html", context)

from django.http import JsonResponse

@login_required
@require_gym_permission("clients.change")
def client_get_stripe_setup(request, client_id):
    """
    Returns a SetupIntent client_secret to link a new card.
    """
    gym_id = request.session.get("current_gym_id")
    client = get_object_or_404(Client, id=client_id, gym_id=gym_id)
    
    try:
        from finance.stripe_utils import create_setup_intent
        client_secret = create_setup_intent(client)
        return JsonResponse({'client_secret': client_secret})
    except Exception as e:
        return JsonResponse({'error': str(e)}, status=400)


@login_required
@require_gym_permission("clients.change")
def client_edit(request, client_id):
    gym_id = request.session.get("current_gym_id")
    if not gym_id:
        return redirect("home")
    
    # Seguridad: Solo clientes del gym actual
    client = get_object_or_404(Client, id=client_id, gym_id=gym_id)

    if request.method == "POST":
        form = ClientForm(request.POST, request.FILES, instance=client)
        if form.is_valid():
            form.save()
            return redirect("client_detail", client_id=client.id)
    else:
        form = ClientForm(instance=client)

    return render(request, "backoffice/clients/form.html", {
        "form": form, 
        "title": f"Editar {client.first_name}"
    })


from .forms import ClientNoteForm, ClientDocumentForm
from .models import ClientNote, ClientDocument
from django.views.decorators.http import require_POST

@login_required
@require_POST
def client_add_note(request, client_id):
    gym_id = request.session.get("current_gym_id")
    client = get_object_or_404(Client, id=client_id, gym_id=gym_id)
    
    form = ClientNoteForm(request.POST)
    if form.is_valid():
        note = form.save(commit=False)
        note.client = client
        note.author = request.user
        note.save()
    
    return redirect("client_detail", client_id=client.id)


@login_required
def client_edit_note(request, note_id):
    gym_id = request.session.get("current_gym_id")
    # Verify note belongs to a client in the current gym
    note = get_object_or_404(ClientNote, id=note_id, client__gym_id=gym_id)
    
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
    gym_id = request.session.get("current_gym_id")
    # Verify note belongs to a client in the current gym
    note = get_object_or_404(ClientNote, id=note_id, client__gym_id=gym_id)
    
    # Optional: Check if user is author or has delete permission
    note.delete()
    return redirect("client_detail", client_id=note.client.id)


@login_required
@require_POST
def client_add_document(request, client_id):
    gym_id = request.session.get("current_gym_id")
    client = get_object_or_404(Client, id=client_id, gym_id=gym_id)
    
    form = ClientDocumentForm(request.POST, request.FILES)
    if form.is_valid():
        doc = form.save(commit=False)
        doc.client = client
        doc.save()
    
    return redirect("client_detail", client_id=client.id)


@login_required
@require_gym_permission("clients.create")
def client_create(request):
    gym_id = request.session.get("current_gym_id")
    if not gym_id:
        return redirect("home")
    
    gym = Gym.objects.filter(id=gym_id).first()
    if not gym:
        return redirect("home")

    if request.method == "POST":
        form = ClientForm(request.POST, request.FILES)
        if form.is_valid():
            client = form.save(commit=False)
            client.gym = gym
            client.save()
            form.save_m2m() # Guardar tags/groups si los hubiera
            return redirect("clients")
    else:
        form = ClientForm()

    return render(request, "backoffice/clients/form.html", {"form": form, "title": "Nuevo Cliente"})
