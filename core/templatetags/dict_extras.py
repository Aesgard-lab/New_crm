"""
Dictionary Template Tags and Filters

Provides utility filters for working with dictionaries in Django templates.
"""
from django import template

register = template.Library()


@register.filter
def get_item(dictionary, key):
    """
    Get an item from a dictionary by key.
    
    Usage:
        {{ my_dict|get_item:key_variable }}
    
    Returns:
        The value associated with the key, or None if not found.
    """
    if dictionary is None:
        return None
    return dictionary.get(key)


@register.filter
def dict_key_exists(dictionary, key):
    """
    Check if a key exists in a dictionary.
    
    Usage:
        {% if my_dict|dict_key_exists:key_variable %}
            Key exists!
        {% endif %}
    
    Returns:
        True if the key exists, False otherwise.
    """
    if dictionary is None:
        return False
    return key in dictionary
