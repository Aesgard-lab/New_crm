from django import template
from django.template import Template, Context

register = template.Library()

@register.filter(name='render_popup_content')
def render_popup_content(popup, client):
    """
    Renderiza el contenido de un popup como template Django,
    permitiendo usar variables como {{ client.first_name }}, {{ popup.get_target_group_display }}, etc.
    """
    try:
        tmpl = Template(popup.content)
        rendered = tmpl.render(Context({
            'popup': popup,
            'client': client,
            'gym': client.gym if hasattr(client, 'gym') else None,
        }))
        return rendered
    except Exception as e:
        # Si falla el render, devolver contenido original
        return popup.content
