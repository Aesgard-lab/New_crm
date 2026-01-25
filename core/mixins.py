"""
Mixins y utilidades comunes para evitar duplicación de código.

Incluye:
- GymContextMixin: Para vistas que necesitan acceso al gym actual
- CachedQueryMixin: Para cachear querysets comunes
- BulkOperationsMixin: Para operaciones bulk eficientes
- FormsetFilterMixin: Para filtrar formsets por gym
"""

import functools
from typing import Any, Dict, List, Optional, Type

from django.contrib.auth.mixins import LoginRequiredMixin
from django.core.cache import cache
from django.db.models import Model, QuerySet
from django.shortcuts import redirect
from django.views import View

from organizations.models import Gym


# ==============================================
# GYM CONTEXT UTILITIES
# ==============================================

class GymContextMixin(LoginRequiredMixin):
    """
    Mixin para vistas basadas en clase que necesitan acceso al gym actual.
    
    Uso:
        class MyView(GymContextMixin, TemplateView):
            template_name = 'my_template.html'
            
            def get_context_data(self, **kwargs):
                context = super().get_context_data(**kwargs)
                context['clients'] = Client.objects.filter(gym=self.gym)
                return context
    """
    
    gym: Optional[Gym] = None
    
    def dispatch(self, request, *args, **kwargs):
        self.gym = get_current_gym(request)
        if not self.gym:
            return redirect('home')
        return super().dispatch(request, *args, **kwargs)
    
    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['gym'] = self.gym
        return context


def get_current_gym(request) -> Optional[Gym]:
    """
    Obtener el gym actual desde el request.
    Función utilitaria para usar en vistas basadas en funciones.
    
    Args:
        request: HttpRequest
        
    Returns:
        Gym o None
    """
    gym = getattr(request, 'gym', None)
    if gym:
        return gym
    
    gym_id = request.session.get('current_gym_id')
    if gym_id:
        return Gym.objects.filter(id=gym_id).first()
    
    return None


def require_gym(view_func):
    """
    Decorador para vistas que requieren un gym.
    Redirige a home si no hay gym.
    
    Uso:
        @login_required
        @require_gym
        def my_view(request):
            gym = request.gym  # Garantizado que existe
            ...
    """
    @functools.wraps(view_func)
    def wrapper(request, *args, **kwargs):
        gym = get_current_gym(request)
        if not gym:
            return redirect('home')
        request.gym = gym
        return view_func(request, *args, **kwargs)
    return wrapper


# ==============================================
# CUSTOM FIELD UTILITIES
# ==============================================

def build_custom_field_options(custom_fields) -> Dict[str, Dict]:
    """
    Construir diccionario de opciones de campos personalizados.
    Función utilitaria para evitar duplicación en múltiples vistas.
    
    Args:
        custom_fields: QuerySet de ClientField
        
    Returns:
        Dict {field_slug: {value: label, ...}}
    """
    from clients.models import ClientField
    
    options = {}
    for field in custom_fields:
        if field.field_type == ClientField.FieldType.TOGGLE:
            options[field.slug] = {True: "Sí", False: "No"}
        else:
            options[field.slug] = {
                opt.value: opt.label 
                for opt in field.options.all()
            }
    return options


def get_client_custom_field_values(client, custom_fields, custom_field_options: Dict) -> Dict:
    """
    Obtener valores de campos personalizados para un cliente.
    
    Args:
        client: Instancia de Client
        custom_fields: QuerySet de ClientField
        custom_field_options: Dict de opciones construido con build_custom_field_options
        
    Returns:
        Dict {field_slug: display_value}
    """
    from clients.models import ClientField
    
    values = {}
    if not isinstance(client.extra_data, dict):
        return values
    
    for field in custom_fields:
        raw_value = client.extra_data.get(field.slug)
        if raw_value is not None and raw_value != "":
            if field.field_type == ClientField.FieldType.TOGGLE:
                values[field.slug] = "Sí" if raw_value else "No"
            else:
                values[field.slug] = custom_field_options.get(
                    field.slug, {}
                ).get(raw_value, raw_value)
    
    return values


# ==============================================
# FORMSET UTILITIES
# ==============================================

def filter_formset_querysets(formset, gym: Gym, field_filters: Dict[str, QuerySet]):
    """
    Filtrar querysets de campos en un formset por gym.
    
    Args:
        formset: Django Formset
        gym: Instancia de Gym
        field_filters: Dict de {field_name: queryset_filtered_by_gym}
        
    Uso:
        filter_formset_querysets(formset, gym, {
            'activity': Activity.objects.filter(gym=gym),
            'room': Room.objects.filter(gym=gym),
        })
    """
    for form in formset:
        for field_name, queryset in field_filters.items():
            if field_name in form.fields:
                form.fields[field_name].queryset = queryset


class FormsetGymFilterMixin:
    """
    Mixin para vistas que usan formsets y necesitan filtrar por gym.
    
    Uso:
        class MyView(FormsetGymFilterMixin, CreateView):
            formset_field_filters = {
                'activity': Activity,
                'room': Room,
            }
    """
    formset_field_filters: Dict[str, Type[Model]] = {}
    
    def filter_formset_by_gym(self, formset):
        """Aplicar filtros de gym al formset."""
        if not hasattr(self, 'gym') or not self.gym:
            return
        
        filters = {}
        for field_name, model_class in self.formset_field_filters.items():
            filters[field_name] = model_class.objects.filter(gym=self.gym)
        
        filter_formset_querysets(formset, self.gym, filters)


# ==============================================
# BULK OPERATIONS
# ==============================================

def bulk_reassign_relations(
    source_obj: Model,
    target_obj: Model,
    relation_names: List[str],
    fk_field: str = 'client'
):
    """
    Reasignar relaciones de un objeto a otro usando bulk operations.
    Útil para fusión de registros.
    
    Args:
        source_obj: Objeto origen (se borrarán sus relaciones)
        target_obj: Objeto destino (recibirá las relaciones)
        relation_names: Lista de nombres de relaciones (related_name)
        fk_field: Nombre del campo FK a actualizar
        
    Uso:
        bulk_reassign_relations(
            old_client, new_client,
            ['notes', 'documents', 'memberships', 'visits'],
            fk_field='client'
        )
    """
    for relation_name in relation_names:
        related_manager = getattr(source_obj, relation_name, None)
        if related_manager is None:
            continue
        
        # Usar update directo en el queryset para evitar N+1
        related_manager.update(**{fk_field: target_obj})


def bulk_copy_m2m_relations(
    source_obj: Model,
    target_obj: Model,
    m2m_names: List[str]
):
    """
    Copiar relaciones ManyToMany de un objeto a otro.
    
    Args:
        source_obj: Objeto origen
        target_obj: Objeto destino
        m2m_names: Lista de nombres de campos M2M
        
    Uso:
        bulk_copy_m2m_relations(old_client, new_client, ['groups', 'tags'])
    """
    for m2m_name in m2m_names:
        source_m2m = getattr(source_obj, m2m_name, None)
        target_m2m = getattr(target_obj, m2m_name, None)
        
        if source_m2m is None or target_m2m is None:
            continue
        
        # Usar add con unpacking para eficiencia
        target_m2m.add(*source_m2m.all())


# ==============================================
# CACHED GYM DATA
# ==============================================

def get_cached_gym_data(gym: Gym, data_type: str, queryset_func, timeout: int = 300):
    """
    Obtener datos de gym cacheados.
    
    Args:
        gym: Instancia de Gym
        data_type: Tipo de datos (ej: 'membership_plans', 'tags')
        queryset_func: Función que retorna el queryset
        timeout: Segundos de cache
        
    Returns:
        Lista de resultados
        
    Uso:
        plans = get_cached_gym_data(
            gym, 'membership_plans',
            lambda: MembershipPlan.objects.filter(gym=gym, is_active=True)
        )
    """
    cache_key = f'gym:{gym.id}:{data_type}'
    cached = cache.get(cache_key)
    
    if cached is not None:
        return cached
    
    result = list(queryset_func())
    cache.set(cache_key, result, timeout)
    
    return result


def invalidate_gym_cache(gym: Gym, data_types: Optional[List[str]] = None):
    """
    Invalidar cache de gym.
    
    Args:
        gym: Instancia de Gym
        data_types: Lista de tipos a invalidar, o None para todos
    """
    if data_types is None:
        data_types = [
            'membership_plans', 'services', 'products', 'tags', 
            'groups', 'custom_fields', 'activities', 'rooms'
        ]
    
    for data_type in data_types:
        cache_key = f'gym:{gym.id}:{data_type}'
        cache.delete(cache_key)


# ==============================================
# QUERY OPTIMIZATION HELPERS
# ==============================================

def optimize_client_queryset(queryset: QuerySet, include_relations: List[str] = None) -> QuerySet:
    """
    Optimizar queryset de clientes con select_related y prefetch_related apropiados.
    
    Args:
        queryset: QuerySet de Client
        include_relations: Lista de relaciones adicionales a incluir
        
    Returns:
        QuerySet optimizado
    """
    # Relaciones básicas siempre incluidas
    queryset = queryset.select_related('gym', 'user')
    
    # Prefetch comunes
    prefetch = ['tags']
    
    if include_relations:
        prefetch.extend(include_relations)
    
    return queryset.prefetch_related(*prefetch)


def optimize_order_queryset(queryset: QuerySet) -> QuerySet:
    """Optimizar queryset de órdenes."""
    return queryset.select_related(
        'client', 'gym', 'session'
    ).prefetch_related(
        'items__content_type',
        'payments__payment_method'
    )


def optimize_session_queryset(queryset: QuerySet) -> QuerySet:
    """Optimizar queryset de sesiones de actividad."""
    return queryset.select_related(
        'activity', 'room', 'staff', 'gym'
    ).prefetch_related('attendees')
