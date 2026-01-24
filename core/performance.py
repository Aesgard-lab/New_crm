"""
Performance optimizations for Django CRM.

This module provides caching utilities and query optimization helpers.
"""

from functools import wraps
from django.core.cache import cache
from django.conf import settings
import hashlib
import json


def cache_page_for_user(timeout=300, key_prefix='page'):
    """
    Cache decorator that includes user and gym context in cache key.
    
    Usage:
        @cache_page_for_user(timeout=60)
        def my_view(request):
            ...
    """
    def decorator(view_func):
        @wraps(view_func)
        def wrapper(request, *args, **kwargs):
            # Build unique cache key
            user_id = request.user.id if request.user.is_authenticated else 'anon'
            gym_id = getattr(request, 'gym', None)
            gym_id = gym_id.id if gym_id else 'no_gym'
            
            # Include query params in key
            query_string = request.GET.urlencode()
            
            key_parts = [
                key_prefix,
                view_func.__name__,
                str(user_id),
                str(gym_id),
                hashlib.md5(query_string.encode()).hexdigest()[:8]
            ]
            cache_key = ':'.join(key_parts)
            
            # Try to get from cache
            response = cache.get(cache_key)
            if response is not None:
                return response
            
            # Generate response
            response = view_func(request, *args, **kwargs)
            
            # Only cache successful GET responses
            if request.method == 'GET' and hasattr(response, 'status_code') and response.status_code == 200:
                cache.set(cache_key, response, timeout)
            
            return response
        return wrapper
    return decorator


def cache_queryset(key, timeout=300, version=None):
    """
    Cache a queryset result.
    
    Usage:
        clients = cache_queryset(
            f'clients_list_{gym_id}',
            timeout=60
        )(lambda: Client.objects.filter(gym_id=gym_id).values_list('id', 'first_name'))()
    """
    def decorator(func):
        @wraps(func)
        def wrapper(*args, **kwargs):
            cached = cache.get(key, version=version)
            if cached is not None:
                return cached
            
            result = func(*args, **kwargs)
            
            # Convert queryset to list for caching
            if hasattr(result, '__iter__') and hasattr(result, 'query'):
                result = list(result)
            
            cache.set(key, result, timeout, version=version)
            return result
        return wrapper
    return decorator


def invalidate_gym_cache(gym_id, prefix=''):
    """
    Invalidate all cache keys for a specific gym.
    Called after data modifications.
    """
    # This is a pattern-based approach
    # For Redis, you'd use SCAN with pattern matching
    patterns = [
        f'{prefix}*gym_{gym_id}*',
        f'clients_*{gym_id}*',
        f'memberships_*{gym_id}*',
        f'finance_*{gym_id}*',
    ]
    
    # With LocMemCache, we can't pattern delete
    # But with Redis backend, you could:
    # for pattern in patterns:
    #     cache.delete_pattern(pattern)
    pass


class QueryOptimizer:
    """
    Helper class for optimizing common queries.
    """
    
    @staticmethod
    def get_clients_optimized(gym, filters=None):
        """
        Optimized client list query with proper prefetching.
        """
        from clients.models import Client
        
        qs = Client.objects.filter(gym=gym).select_related(
            'gym'
        ).prefetch_related(
            'tags',
            'memberships',
            'memberships__plan',
        ).only(
            'id', 'first_name', 'last_name', 'email', 'phone_number',
            'status', 'photo', 'dni', 'is_company_client', 'created_at',
            'preferred_gateway', 'stripe_customer_id', 'extra_data',
            'gym_id'
        )
        
        if filters:
            if filters.get('status') and filters['status'] != 'all':
                qs = qs.filter(status=filters['status'])
            if filters.get('q'):
                from django.db.models import Q
                q = filters['q']
                qs = qs.filter(
                    Q(first_name__icontains=q) |
                    Q(last_name__icontains=q) |
                    Q(email__icontains=q) |
                    Q(phone_number__icontains=q)
                )
        
        return qs.order_by('-created_at')
    
    @staticmethod
    def get_orders_optimized(gym, date_from=None, date_to=None):
        """
        Optimized orders query for billing dashboard.
        """
        from sales.models import Order
        
        qs = Order.objects.filter(gym=gym).select_related(
            'client',
            'created_by',
        ).prefetch_related(
            'items',
            'payments',
            'payments__payment_method',
        )
        
        if date_from:
            qs = qs.filter(created_at__gte=date_from)
        if date_to:
            qs = qs.filter(created_at__lte=date_to)
        
        return qs.order_by('-created_at')
    
    @staticmethod
    def get_memberships_for_billing(gym):
        """
        Optimized membership query for scheduled billing.
        """
        from memberships.models import ClientMembership
        from django.utils import timezone
        
        return ClientMembership.objects.filter(
            gym=gym,
            status='ACTIVE',
            is_recurring=True,
        ).select_related(
            'client',
            'plan',
        ).only(
            'id', 'name', 'price', 'end_date', 'next_billing_date',
            'failed_charge_attempts', 'last_charge_error',
            'client__id', 'client__first_name', 'client__last_name',
            'client__stripe_customer_id', 'client__preferred_gateway',
            'plan__id', 'plan__name',
        ).order_by('end_date')


# Database index suggestions (run as migration)
DATABASE_INDEX_SUGGESTIONS = """
-- Índices recomendados para mejorar rendimiento

-- Clientes
CREATE INDEX CONCURRENTLY IF NOT EXISTS idx_client_gym_status 
ON clients_client(gym_id, status);

CREATE INDEX CONCURRENTLY IF NOT EXISTS idx_client_gym_created 
ON clients_client(gym_id, created_at DESC);

CREATE INDEX CONCURRENTLY IF NOT EXISTS idx_client_email_gin 
ON clients_client USING gin(email gin_trgm_ops);

-- Membresías
CREATE INDEX CONCURRENTLY IF NOT EXISTS idx_membership_gym_status 
ON memberships_clientmembership(gym_id, status);

CREATE INDEX CONCURRENTLY IF NOT EXISTS idx_membership_client_status 
ON memberships_clientmembership(client_id, status);

CREATE INDEX CONCURRENTLY IF NOT EXISTS idx_membership_end_date 
ON memberships_clientmembership(end_date) WHERE status = 'ACTIVE';

-- Órdenes/Ventas
CREATE INDEX CONCURRENTLY IF NOT EXISTS idx_order_gym_created 
ON sales_order(gym_id, created_at DESC);

CREATE INDEX CONCURRENTLY IF NOT EXISTS idx_order_client 
ON sales_order(client_id, created_at DESC);

-- Pagos
CREATE INDEX CONCURRENTLY IF NOT EXISTS idx_payment_order 
ON sales_orderpayment(order_id);

-- Sesiones de actividades
CREATE INDEX CONCURRENTLY IF NOT EXISTS idx_session_gym_date 
ON activities_activitysession(gym_id, date, start_time);

-- Reservas
CREATE INDEX CONCURRENTLY IF NOT EXISTS idx_booking_session 
ON activities_booking(session_id, status);

CREATE INDEX CONCURRENTLY IF NOT EXISTS idx_booking_client 
ON activities_booking(client_id, created_at DESC);
"""
