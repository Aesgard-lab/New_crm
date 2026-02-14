"""
Template tags personalizados para analytics.
"""
from django import template
import json
from django.core.serializers.json import DjangoJSONEncoder
from django.utils.safestring import mark_safe

register = template.Library()


@register.filter
def dict_get(dictionary, key):
    """
    Obtener valor de un diccionario por clave.
    Uso: {{ mydict|dict_get:"mykey" }}
    """
    if dictionary is None:
        return None
    
    # Si no es un diccionario, retornar None
    if not isinstance(dictionary, dict):
        return None
    
    # Convertir key a int si es posible (para heatmap)
    try:
        key = int(key)
    except (ValueError, TypeError):
        pass
    
    return dictionary.get(key)


@register.filter
def get_heatmap_cell(dictionary, key):
    """
    Obtiene valor de diccionario, manejando claves numéricas o strings.
    Específico para heatmap.
    """
    if not dictionary or not isinstance(dictionary, dict):
        return None
        
    # Intentar como int (común en heatmap keys)
    try:
        int_key = int(key)
        if int_key in dictionary:
            return dictionary[int_key]
    except (ValueError, TypeError):
        pass
        
    # Intentar como string
    str_key = str(key)
    if str_key in dictionary:
        return dictionary[str_key]
        
    return None


@register.filter
def div(value, arg):
    """
    Divide un valor por un argumento.
    Uso: {{ value|div:50 }}
    """
    try:
        return float(value) / float(arg)
    except (ValueError, ZeroDivisionError, TypeError):
        return 0


@register.filter
def mul(value, arg):
    """
    Multiplica un valor por un argumento.
    Uso: {{ value|mul:50 }}
    """
    try:
        return float(value) * float(arg)
    except (ValueError, TypeError):
        return 0


@register.filter
def sub(value, arg):
    """
    Resta un argumento de un valor.
    Uso: {{ value|sub:50 }}
    """
    try:
        return float(value) - float(arg)
    except (ValueError, TypeError):
        return 0


@register.filter
def safe_json(value):
    """
    Serializa un valor a JSON de forma segura para usar en templates.
    Uso: {{ mydata|safe_json }}
    """
    try:
        return mark_safe(json.dumps(value, cls=DjangoJSONEncoder))
    except (TypeError, ValueError):
        return "{}"


@register.simple_tag
def hour_range(start=6, end=22):
    """
    Genera un rango de horas.
    Uso: {% hour_range 6 22 as hours %}
    """
    return list(range(start, end))


@register.simple_tag
def day_range():
    """
    Genera lista de días (1=Lun a 7=Dom).
    Uso: {% day_range as days %}
    """
    return [1, 2, 3, 4, 5, 6, 7]
