"""
Utilidades para envío de emails usando la configuración SMTP del gimnasio.
"""
from django.core.mail import EmailMessage, EmailMultiAlternatives
from django.core.mail.backends.smtp import EmailBackend
from django.template.loader import render_to_string
from django.utils.html import strip_tags
from django.conf import settings
import os


def get_gym_email_backend(gym):
    """
    Crea un backend SMTP configurado con los datos del gimnasio.
    """
    if not gym.smtp_host:
        raise ValueError("El gimnasio no tiene configuración SMTP")
    
    return EmailBackend(
        host=gym.smtp_host,
        port=gym.smtp_port,
        username=gym.smtp_username,
        password=gym.smtp_password,
        use_tls=gym.smtp_use_tls,
        use_ssl=gym.smtp_use_ssl,
        fail_silently=False,
        timeout=30
    )


def send_gym_email(gym, subject, body, to_emails, html_body=None, attachments=None, base_url=None):
    """
    Envía un email usando la configuración SMTP del gimnasio.
    Añade automáticamente la firma (con logo si existe) y el footer configurados.
    
    Args:
        gym: Instancia del modelo Gym
        subject: Asunto del email
        body: Cuerpo del email en texto plano
        to_emails: Lista de emails destinatarios o un solo email
        html_body: (Opcional) Cuerpo HTML del email
        attachments: (Opcional) Lista de tuplas (filename, content, mimetype)
        base_url: (Opcional) URL base para construir URLs absolutas de imágenes
    
    Returns:
        int: Número de emails enviados (1 si éxito, 0 si fallo)
    """
    if isinstance(to_emails, str):
        to_emails = [to_emails]
    
    # Obtener datos del remitente
    from_email = gym.smtp_from_email or gym.smtp_username or gym.email
    sender_name = gym.commercial_name or gym.name
    from_address = f'{sender_name} <{from_email}>'
    
    # Construir el cuerpo con firma y footer
    full_body = body
    full_html = html_body
    
    # Si no hay HTML, crear uno básico
    if not full_html:
        full_html = f"<div style='font-family: Arial, sans-serif; font-size: 14px; color: #333;'>{body.replace(chr(10), '<br>')}</div>"
    
    # Construir la firma HTML con logo si existe
    signature_html = ""
    if gym.email_signature_logo or gym.email_signature:
        signature_html = "<div style='margin-top: 30px; padding-top: 20px; border-top: 1px solid #e5e7eb;'>"
        
        # Añadir logo si existe
        if gym.email_signature_logo:
            # Construir URL absoluta del logo
            if base_url:
                logo_url = f"{base_url}{gym.email_signature_logo.url}"
            else:
                logo_url = gym.email_signature_logo.url
            signature_html += f"<img src='{logo_url}' alt='{sender_name}' style='max-height: 80px; width: auto; margin-bottom: 10px;'><br>"
        
        # Añadir texto de firma si existe
        if gym.email_signature:
            signature_html += f"<div style='color: #374151; font-size: 13px;'>{gym.email_signature.replace(chr(10), '<br>')}</div>"
        
        signature_html += "</div>"
    
    # Añadir firma al texto plano
    if gym.email_signature:
        full_body += f"\n\n---\n{gym.email_signature}"
    
    # Añadir firma HTML
    if signature_html:
        full_html += signature_html
    
    # Añadir footer si existe
    if gym.email_footer:
        full_body += f"\n\n{gym.email_footer}"
        full_html += f"<div style='font-size: 11px; color: #6b7280; margin-top: 30px; padding-top: 20px; border-top: 1px solid #e5e7eb;'>{gym.email_footer.replace(chr(10), '<br>')}</div>"
    
    # Crear el backend
    backend = get_gym_email_backend(gym)
    
    # Email con HTML y texto plano alternativo
    email = EmailMultiAlternatives(
        subject=subject,
        body=full_body,
        from_email=from_address,
        to=to_emails,
        connection=backend
    )
    email.attach_alternative(full_html, "text/html")
    
    # Añadir adjuntos si los hay
    if attachments:
        for filename, content, mimetype in attachments:
            email.attach(filename, content, mimetype)
    
    return email.send()


def send_gym_template_email(gym, subject, template_name, context, to_emails, attachments=None):
    """
    Envía un email usando un template Django.
    
    Args:
        gym: Instancia del modelo Gym
        subject: Asunto del email
        template_name: Nombre del template (ej: 'emails/welcome.html')
        context: Diccionario con el contexto para el template
        to_emails: Lista de emails destinatarios o un solo email
        attachments: (Opcional) Lista de tuplas (filename, content, mimetype)
    
    Returns:
        int: Número de emails enviados
    """
    # Añadir datos del gimnasio al contexto
    context['gym'] = gym
    context['gym_name'] = gym.commercial_name or gym.name
    
    # Renderizar el template
    html_body = render_to_string(template_name, context)
    text_body = strip_tags(html_body)
    
    return send_gym_email(
        gym=gym,
        subject=subject,
        body=text_body,
        to_emails=to_emails,
        html_body=html_body,
        attachments=attachments
    )
