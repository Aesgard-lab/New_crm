from django import template
from accounts.permissions import user_has_gym_permission

register = template.Library()

@register.simple_tag(takes_context=True)
def has_gym_perm(context, perm_code):
    """
    Uso en template:
    {% has_gym_perm 'clients.create' as can_create %}
    {% if can_create %} ... {% endif %}
    """
    request = context.get('request')
    if not request or not request.user.is_authenticated:
        return False

    gym_id = request.session.get("current_gym_id")
    if not gym_id:
        return False

    return user_has_gym_permission(request.user, gym_id, perm_code)
