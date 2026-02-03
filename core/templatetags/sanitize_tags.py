"""
Template tags para sanitización segura de HTML.

SECURITY: Estos filtros previenen XSS al sanitizar HTML antes de renderizar.

Uso:
    {% load sanitize_tags %}
    {{ content|sanitize_html }}
    {{ content|sanitize_html_strict }}
"""
from django import template
from django.utils.safestring import mark_safe
import re

register = template.Library()

# Tags HTML permitidos por nivel de restricción
ALLOWED_TAGS_BASIC = [
    'b', 'i', 'u', 'strong', 'em', 'br', 'p', 'span'
]

ALLOWED_TAGS_STANDARD = ALLOWED_TAGS_BASIC + [
    'ul', 'ol', 'li', 'a', 'h1', 'h2', 'h3', 'h4', 'h5', 'h6',
    'blockquote', 'pre', 'code', 'hr', 'div', 'table', 'thead',
    'tbody', 'tr', 'th', 'td', 'img', 'figure', 'figcaption'
]

ALLOWED_ATTRS = {
    'a': ['href', 'title', 'target', 'rel'],
    'img': ['src', 'alt', 'title', 'width', 'height'],
    'span': ['class', 'style'],
    'div': ['class', 'style'],
    'p': ['class', 'style'],
    'table': ['class', 'border'],
    'th': ['colspan', 'rowspan'],
    'td': ['colspan', 'rowspan'],
    '*': ['class']  # class permitido en todos
}

# Estilos CSS permitidos
ALLOWED_STYLES = [
    'color', 'background-color', 'font-size', 'font-weight', 
    'font-style', 'text-align', 'text-decoration', 'margin',
    'padding', 'border'
]


def _simple_sanitize(html_content, allowed_tags):
    """
    Sanitización simple sin dependencias externas.
    Elimina tags no permitidos pero preserva su contenido.
    """
    if not html_content:
        return ''
    
    # Convertir a string si no lo es
    content = str(html_content)
    
    # Eliminar scripts y event handlers (alta prioridad)
    content = re.sub(r'<script[^>]*>.*?</script>', '', content, flags=re.IGNORECASE | re.DOTALL)
    content = re.sub(r'<style[^>]*>.*?</style>', '', content, flags=re.IGNORECASE | re.DOTALL)
    content = re.sub(r'\s*on\w+\s*=\s*["\'][^"\']*["\']', '', content, flags=re.IGNORECASE)
    content = re.sub(r'\s*on\w+\s*=\s*[^\s>]+', '', content, flags=re.IGNORECASE)
    
    # Eliminar javascript: y data: URLs
    content = re.sub(r'javascript\s*:', '', content, flags=re.IGNORECASE)
    content = re.sub(r'data\s*:', 'data-blocked:', content, flags=re.IGNORECASE)
    content = re.sub(r'vbscript\s*:', '', content, flags=re.IGNORECASE)
    
    # Crear patrón para tags permitidos
    allowed_pattern = '|'.join(allowed_tags)
    
    # Eliminar tags no permitidos pero mantener contenido
    # Esto elimina tags de apertura y cierre que no estén en la lista
    def remove_disallowed_tags(match):
        tag = match.group(1).lower().split()[0]  # Obtener nombre del tag
        if tag in allowed_tags or tag.startswith('/') and tag[1:] in allowed_tags:
            return match.group(0)  # Mantener el tag
        return ''  # Eliminar el tag pero no el contenido entre tags
    
    content = re.sub(r'<(/?\w+)([^>]*)>', remove_disallowed_tags, content)
    
    return content


try:
    import bleach
    BLEACH_AVAILABLE = True
except ImportError:
    BLEACH_AVAILABLE = False


@register.filter(name='sanitize_html')
def sanitize_html(value):
    """
    Sanitiza HTML permitiendo un conjunto seguro de tags y atributos.
    
    Uso: {{ content|sanitize_html }}
    """
    if not value:
        return ''
    
    if BLEACH_AVAILABLE:
        clean_html = bleach.clean(
            str(value),
            tags=ALLOWED_TAGS_STANDARD,
            attributes=ALLOWED_ATTRS,
            strip=True
        )
        # Linkificar URLs si existen
        clean_html = bleach.linkify(clean_html)
        return mark_safe(clean_html)
    else:
        # Fallback sin bleach
        return mark_safe(_simple_sanitize(str(value), ALLOWED_TAGS_STANDARD))


@register.filter(name='sanitize_html_strict')
def sanitize_html_strict(value):
    """
    Sanitiza HTML con reglas estrictas (solo formateo básico).
    
    Uso: {{ content|sanitize_html_strict }}
    """
    if not value:
        return ''
    
    if BLEACH_AVAILABLE:
        clean_html = bleach.clean(
            str(value),
            tags=ALLOWED_TAGS_BASIC,
            attributes={},
            strip=True
        )
        return mark_safe(clean_html)
    else:
        # Fallback sin bleach
        return mark_safe(_simple_sanitize(str(value), ALLOWED_TAGS_BASIC))


@register.filter(name='sanitize_plain')
def sanitize_plain(value):
    """
    Elimina TODO el HTML y devuelve solo texto plano.
    
    Uso: {{ content|sanitize_plain }}
    """
    if not value:
        return ''
    
    if BLEACH_AVAILABLE:
        return bleach.clean(str(value), tags=[], strip=True)
    else:
        # Eliminar todos los tags HTML
        return re.sub(r'<[^>]+>', '', str(value))


@register.filter(name='safe_json')
def safe_json(value):
    """
    Escapa contenido para uso seguro dentro de bloques <script>.
    Previene XSS en datos JSON insertados en templates.
    
    Uso: <script>var data = {{ data|safe_json }};</script>
    """
    import json
    from django.utils.html import escapejs
    
    if value is None:
        return 'null'
    
    # Serializar a JSON
    json_str = json.dumps(value)
    
    # Escapar caracteres peligrosos para contexto HTML/JS
    # </script> podría cerrar el bloque script prematuramente
    json_str = json_str.replace('</', '<\\/')
    json_str = json_str.replace('<!--', '<\\!--')
    
    return mark_safe(json_str)
