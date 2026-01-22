"""
Template tags personalizados para analytics.
"""
from django import template

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
def div(value, arg):
    """
    Divide un valor por un argumento.
    Uso: {{ value|div:50 }}
    """
    try:
        return float(value) / float(arg)
    except (ValueError, ZeroDivisionError, TypeError):
        return 0


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
