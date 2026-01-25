"""
Feature Flags Template Tags

Permite usar feature flags en templates de Django.
"""
from django import template
from ..feature_flags import FeatureFlagService

register = template.Library()


@register.simple_tag(takes_context=True)
def feature_enabled(context, flag_name):
    """
    Verifica si un feature flag esta activo.
    
    Usage:
        {% feature_enabled 'new_feature' as is_enabled %}
        {% if is_enabled %}
            <div>New Feature Content</div>
        {% endif %}
    """
    request = context.get('request')
    user = getattr(request, 'user', None) if request else None
    return FeatureFlagService.is_enabled(flag_name, user)


@register.tag
def iffeature(parser, token):
    """
    Tag condicional para feature flags.
    
    Usage:
        {% iffeature 'new_feature' %}
            <div>This is a new feature!</div>
        {% else %}
            <div>Old feature</div>
        {% endiffeature %}
    """
    bits = token.split_contents()
    if len(bits) != 2:
        raise template.TemplateSyntaxError(
            f"'{bits[0]}' tag requires exactly one argument"
        )
    flag_name = bits[1]
    
    # Remove quotes if present
    if flag_name[0] in ('"', "'"):
        flag_name = flag_name[1:-1]
    
    nodelist_true = parser.parse(('else', 'endiffeature'))
    token = parser.next_token()
    
    if token.contents == 'else':
        nodelist_false = parser.parse(('endiffeature',))
        parser.delete_first_token()
    else:
        nodelist_false = template.NodeList()
    
    return IfFeatureNode(flag_name, nodelist_true, nodelist_false)


class IfFeatureNode(template.Node):
    def __init__(self, flag_name, nodelist_true, nodelist_false):
        self.flag_name = flag_name
        self.nodelist_true = nodelist_true
        self.nodelist_false = nodelist_false
    
    def render(self, context):
        request = context.get('request')
        user = getattr(request, 'user', None) if request else None
        
        if FeatureFlagService.is_enabled(self.flag_name, user):
            return self.nodelist_true.render(context)
        return self.nodelist_false.render(context)


@register.inclusion_tag('core/feature_flags_list.html', takes_context=True)
def show_feature_flags(context):
    """
    Muestra lista de feature flags activos (solo para desarrollo).
    
    Usage:
        {% show_feature_flags %}
    """
    request = context.get('request')
    user = getattr(request, 'user', None) if request else None
    enabled_flags = FeatureFlagService.get_enabled_flags_for_user(user)
    
    return {
        'enabled_flags': enabled_flags,
        'show_debug': getattr(request, 'user', None) and request.user.is_superuser
    }
