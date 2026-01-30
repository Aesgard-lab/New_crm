from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.core.paginator import Paginator
from django.db.models import Q
from django.forms import inlineformset_factory
from django.shortcuts import render, redirect, get_object_or_404
from accounts.decorators import require_gym_permission
from .models import Provider, PurchaseOrder, PurchaseOrderLine
from .forms import ProviderForm, PurchaseOrderForm, PurchaseOrderLineForm, PurchaseOrderLineFormSet


@login_required
@require_gym_permission("providers.view")
def provider_list(request):
    gym = request.gym
    q = request.GET.get("q", "").strip()
    queryset = Provider.objects.filter(gym=gym).select_related("gym").prefetch_related("contacts", "items")
    if q:
        queryset = queryset.filter(Q(name__icontains=q) | Q(legal_name__icontains=q) | Q(tax_id__icontains=q))

    paginator = Paginator(queryset, 20)
    page_obj = paginator.get_page(request.GET.get("page"))
    return render(
        request,
        "backoffice/providers/list.html",
        {
            "providers": page_obj,
            "page_obj": page_obj,
            "q": q,
        },
    )


@login_required
@require_gym_permission("providers.manage")
def provider_create(request):
    gym = request.gym
    if request.method == "POST":
        form = ProviderForm(request.POST)
        if form.is_valid():
            provider = form.save(commit=False)
            provider.gym = gym
            provider.save()
            messages.success(request, "Proveedor creado.")
            return redirect("providers:provider_list")
    else:
        form = ProviderForm()

    return render(
        request,
        "backoffice/providers/form.html",
        {
            "form": form,
            "title": "Nuevo proveedor",
        },
    )


@login_required
@require_gym_permission("providers.manage")
def provider_edit(request, pk):
    gym = request.gym
    provider = get_object_or_404(Provider, pk=pk, gym=gym)

    if request.method == "POST":
        form = ProviderForm(request.POST, instance=provider)
        if form.is_valid():
            form.save()
            messages.success(request, "Proveedor actualizado.")
            return redirect("providers:provider_list")
    else:
        form = ProviderForm(instance=provider)

    return render(
        request,
        "backoffice/providers/form.html",
        {
            "form": form,
            "title": f"Editar {provider.name}",
        },
    )


@login_required
@require_gym_permission("providers.purchase_orders.view")
def purchase_order_list(request):
    gym = request.gym
    q = request.GET.get("q", "").strip()
    status = request.GET.get("status", "").strip()
    provider_id = request.GET.get("provider")

    queryset = (
        PurchaseOrder.objects.filter(gym=gym)
        .select_related("provider", "created_by")
        .prefetch_related("lines")
        .order_by("-created_at")
    )
    if q:
        queryset = queryset.filter(Q(reference__icontains=q) | Q(provider__name__icontains=q))
    if status:
        queryset = queryset.filter(status=status)
    if provider_id:
        queryset = queryset.filter(provider_id=provider_id)

    paginator = Paginator(queryset, 20)
    page_obj = paginator.get_page(request.GET.get("page"))
    return render(
        request,
        "backoffice/providers/purchase_orders.html",
        {
            "purchase_orders": page_obj,
            "page_obj": page_obj,
            "q": q,
            "status": status,
            "provider_id": provider_id,
            "providers": Provider.objects.filter(gym=gym).only("id", "name"),
        },
    )


@login_required
@require_gym_permission("providers.purchase_orders.manage")
def purchase_order_create(request):
    gym = request.gym
    LineFormSet = PurchaseOrderLineFormSet
    if request.method == "POST":
        form = PurchaseOrderForm(request.POST, gym=gym)
        formset = LineFormSet(request.POST, prefix="lines")
        if form.is_valid() and formset.is_valid():
            po = form.save(commit=False)
            po.gym = gym
            po.created_by = request.user
            po.save()
            formset.instance = po
            formset.save()
            messages.success(request, "Orden de compra creada.")
            return redirect("providers:purchase_order_list")
    else:
        form = PurchaseOrderForm(gym=gym)
        formset = LineFormSet(prefix="lines")

    return render(
        request,
        "backoffice/providers/purchase_order_form.html",
        {
            "form": form,
            "formset": formset,
            "title": "Nueva orden de compra",
        },
    )


@login_required
@require_gym_permission("providers.purchase_orders.manage")
def purchase_order_edit(request, pk):
    gym = request.gym
    po = get_object_or_404(PurchaseOrder, pk=pk, gym=gym)
    LineFormSet = PurchaseOrderLineFormSet

    if request.method == "POST":
        form = PurchaseOrderForm(request.POST, instance=po, gym=gym)
        formset = LineFormSet(request.POST, instance=po, prefix="lines")
        # pasar gym/provider a cada form del formset
        for f in formset.forms:
            f.__init__(data=f.data, instance=f.instance, gym=gym, provider=po.provider)
        if form.is_valid() and formset.is_valid():
            po = form.save(commit=False)
            po.gym = gym
            po.save()
            formset.save()
            messages.success(request, "Orden de compra actualizada.")
            return redirect("providers:purchase_order_list")
    else:
        form = PurchaseOrderForm(instance=po, gym=gym)
        formset = LineFormSet(instance=po, prefix="lines")
        for f in formset.forms:
            f.__init__(instance=f.instance, gym=gym, provider=po.provider)

    return render(
        request,
        "backoffice/providers/purchase_order_form.html",
        {
            "form": form,
            "formset": formset,
            "title": f"Editar PO-{po.id}",
        },
    )


# ==========================================
# EXPORT FUNCTIONS
# ==========================================
from django.http import HttpResponse
from django.utils import timezone
from core.export_service import GenericExportService, ExportConfig


@login_required
@require_gym_permission("providers.view")
def provider_export_excel(request):
    """Exporta listado de proveedores a Excel"""
    gym = request.gym
    providers = Provider.objects.filter(gym=gym).prefetch_related('contacts')
    
    config = ExportConfig(
        title="Listado de Proveedores",
        headers=['ID', 'Nombre', 'Razón Social', 'CIF/NIF', 'Email', 'Teléfono', 'Ciudad', 'País'],
        data_extractor=lambda p: [
            p.id,
            p.name,
            p.legal_name or '-',
            p.tax_id or '-',
            p.email or '-',
            p.phone or '-',
            p.city or '-',
            p.country or '-',
        ],
        column_widths=[8, 25, 25, 15, 25, 15, 15, 12]
    )
    
    excel_file = GenericExportService.export_to_excel(providers.order_by('name'), config, gym.name)
    
    response = HttpResponse(
        excel_file.read(),
        content_type='application/vnd.openxmlformats-officedocument.spreadsheetml.sheet'
    )
    response['Content-Disposition'] = f'attachment; filename="proveedores_{gym.name}_{timezone.now().strftime("%Y%m%d")}.xlsx"'
    return response


@login_required
@require_gym_permission("providers.view")
def provider_export_pdf(request):
    """Exporta listado de proveedores a PDF"""
    gym = request.gym
    providers = Provider.objects.filter(gym=gym).prefetch_related('contacts')
    
    config = ExportConfig(
        title="Listado de Proveedores",
        headers=['Nombre', 'Razón Social', 'CIF/NIF', 'Email', 'Teléfono'],
        data_extractor=lambda p: [
            p.name,
            p.legal_name or '-',
            p.tax_id or '-',
            p.email or '-',
            p.phone or '-',
        ],
        column_widths=[22, 22, 15, 25, 15],
        landscape=True
    )
    
    pdf_file = GenericExportService.export_to_pdf(providers.order_by('name'), config, gym.name)
    
    response = HttpResponse(pdf_file.read(), content_type='application/pdf')
    response['Content-Disposition'] = f'attachment; filename="proveedores_{gym.name}_{timezone.now().strftime("%Y%m%d")}.pdf"'
    return response
