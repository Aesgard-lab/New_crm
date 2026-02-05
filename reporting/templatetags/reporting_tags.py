from django import template

register = template.Library()


@register.filter
def get_item(dictionary, key):
    """
    Obtiene un item de un diccionario por clave.
    Uso: {{ mydict|get_item:key }}
    """
    if dictionary is None:
        return None
    if isinstance(dictionary, dict):
        return dictionary.get(key)
    return None


@register.filter
def get_index(lst, index):
    """
    Obtiene un elemento de una lista por índice.
    Uso: {{ mylist|get_index:0 }}
    """
    if lst is None:
        return None
    try:
        return lst[int(index)]
    except (IndexError, ValueError, TypeError):
        return None


@register.filter
def multiply(value, arg):
    """
    Multiplica dos valores.
    Uso: {{ value|multiply:2 }}
    """
    try:
        return float(value) * float(arg)
    except (ValueError, TypeError):
        return 0


@register.filter
def divide(value, arg):
    """
    Divide dos valores.
    Uso: {{ value|divide:2 }}
    """
    try:
        return float(value) / float(arg)
    except (ValueError, TypeError, ZeroDivisionError):
        return 0


@register.filter
def subtract(value, arg):
    """
    Resta dos valores.
    Uso: {{ value|subtract:10 }}
    """
    try:
        return float(value) - float(arg)
    except (ValueError, TypeError):
        return 0


@register.filter
def percentage(value, total):
    """
    Calcula el porcentaje de value sobre total.
    Uso: {{ value|percentage:total }}
    """
    try:
        if float(total) == 0:
            return 0
        return (float(value) / float(total)) * 100
    except (ValueError, TypeError):
        return 0


@register.filter
def format_currency(value, decimals=2):
    """
    Formatea un número como moneda.
    Uso: {{ value|format_currency }}
    """
    try:
        return f"{float(value):,.{int(decimals)}f}".replace(",", "X").replace(".", ",").replace("X", ".")
    except (ValueError, TypeError):
        return "0,00"


@register.filter
def growth_class(value):
    """
    Retorna clase CSS según el valor de crecimiento.
    Uso: {{ value|growth_class }}
    """
    try:
        val = float(value)
        if val > 0:
            return "text-green-600"
        elif val < 0:
            return "text-red-600"
        return "text-gray-600"
    except (ValueError, TypeError):
        return "text-gray-600"


@register.filter
def growth_icon(value):
    """
    Retorna icono según el valor de crecimiento.
    Uso: {{ value|growth_icon }}
    """
    try:
        val = float(value)
        if val > 0:
            return "↑"
        elif val < 0:
            return "↓"
        return "="
    except (ValueError, TypeError):
        return "="


@register.simple_tag
def calc_growth(current, previous):
    """
    Calcula el porcentaje de crecimiento.
    Uso: {% calc_growth current previous %}
    """
    try:
        curr = float(current)
        prev = float(previous)
        if prev == 0:
            return 100.0 if curr > 0 else 0.0
        return ((curr - prev) / prev) * 100
    except (ValueError, TypeError):
        return 0.0
