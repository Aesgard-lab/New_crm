"""
Unified Email Service for the platform.

This service provides a centralized way to send emails, automatically choosing
between the gym's own SMTP configuration or the platform's Mailrelay service.

Priority:
1. If gym has SMTP configured → Use gym's SMTP
2. If gym's plan includes transactional email → Use Mailrelay
3. Otherwise → Raise error or return False

Usage:
    from core.email_service import send_email, send_template_email
    
    # Simple email
    result = send_email(
        gym=gym,
        to='cliente@email.com',
        subject='Tu factura',
        body='Adjuntamos tu factura...',
        html_body='<p>Adjuntamos tu factura...</p>'
    )
    
    # Template email
    result = send_template_email(
        gym=gym,
        to='cliente@email.com',
        subject='Bienvenido',
        template='emails/welcome.html',
        context={'user': user}
    )
"""
import logging
import requests
from typing import Optional, Union, List, Tuple
from django.conf import settings
from django.core.mail import EmailMultiAlternatives
from django.core.mail.backends.smtp import EmailBackend
from django.template.loader import render_to_string
from django.utils.html import strip_tags

logger = logging.getLogger(__name__)


class EmailServiceError(Exception):
    """Base exception for email service errors"""
    pass


class NoEmailConfigurationError(EmailServiceError):
    """Raised when gym has no email configuration available"""
    pass


class EmailLimitExceededError(EmailServiceError):
    """Raised when gym has exceeded their email limit"""
    pass


class MailrelayError(EmailServiceError):
    """Raised when Mailrelay API returns an error"""
    pass


def _get_billing_config():
    """Get the platform's billing configuration"""
    from saas_billing.models import BillingConfig
    return BillingConfig.get_config()


def _get_gym_subscription(gym):
    """Get the gym's subscription plan"""
    try:
        return gym.subscription
    except Exception:
        return None


def _check_email_limits(gym, subscription) -> Tuple[bool, str]:
    """
    Check if the gym can send more transactional emails.
    Returns (can_send, error_message)
    """
    from saas_billing.models import GymEmailUsage
    
    plan = subscription.plan if subscription else None
    
    if not plan:
        return False, "El gimnasio no tiene un plan activo"
    
    if not plan.module_transactional_email:
        return False, "El plan no incluye email transaccional"
    
    # Check daily limit
    if plan.transactional_email_limit_daily:
        daily_count = GymEmailUsage.get_daily_count(gym)
        if daily_count >= plan.transactional_email_limit_daily:
            return False, f"Límite diario de emails alcanzado ({plan.transactional_email_limit_daily})"
    
    # Check monthly limit
    if plan.transactional_email_limit_monthly:
        monthly_count = GymEmailUsage.get_monthly_count(gym)
        if monthly_count >= plan.transactional_email_limit_monthly:
            return False, f"Límite mensual de emails alcanzado ({plan.transactional_email_limit_monthly})"
    
    return True, ""


def _increment_email_usage(gym):
    """Increment the email usage counter for the gym"""
    from saas_billing.models import GymEmailUsage
    GymEmailUsage.increment_usage(gym)


def _has_smtp_configured(gym) -> bool:
    """Check if the gym has SMTP configured"""
    return bool(gym.smtp_host and gym.smtp_username and gym.smtp_password)


def _send_via_gym_smtp(
    gym,
    to_emails: List[str],
    subject: str,
    body: str,
    html_body: Optional[str] = None,
    attachments: Optional[List[Tuple]] = None
) -> bool:
    """Send email using the gym's own SMTP configuration"""
    try:
        # Get sender info
        from_email = gym.smtp_from_email or gym.smtp_username or gym.email
        sender_name = gym.commercial_name or gym.name
        from_address = f'{sender_name} <{from_email}>'
        
        # Create backend
        backend = EmailBackend(
            host=gym.smtp_host,
            port=gym.smtp_port,
            username=gym.smtp_username,
            password=gym.smtp_password,
            use_tls=gym.smtp_use_tls,
            use_ssl=gym.smtp_use_ssl,
            fail_silently=False,
            timeout=30
        )
        
        # Prepare HTML if not provided
        if not html_body:
            html_body = f"<div style='font-family: Arial, sans-serif;'>{body.replace(chr(10), '<br>')}</div>"
        
        # Add signature and footer
        full_body, full_html = _add_gym_signature(gym, body, html_body)
        
        # Create email
        email = EmailMultiAlternatives(
            subject=subject,
            body=full_body,
            from_email=from_address,
            to=to_emails,
            connection=backend
        )
        email.attach_alternative(full_html, "text/html")
        
        # Add attachments
        if attachments:
            for filename, content, mimetype in attachments:
                email.attach(filename, content, mimetype)
        
        result = email.send()
        logger.info(f"Email sent via gym SMTP: {gym.name} -> {to_emails}")
        return result > 0
        
    except Exception as e:
        logger.error(f"Failed to send email via gym SMTP ({gym.name}): {str(e)}")
        raise EmailServiceError(f"Error enviando email por SMTP: {str(e)}")


def _send_via_mailrelay(
    gym,
    to_emails: List[str],
    subject: str,
    body: str,
    html_body: Optional[str] = None
) -> bool:
    """Send email using the platform's Mailrelay service"""
    config = _get_billing_config()
    
    if not config.mailrelay_enabled:
        raise NoEmailConfigurationError("El servicio Mailrelay no está habilitado en la plataforma")
    
    if not config.mailrelay_api_key:
        raise NoEmailConfigurationError("No hay API key de Mailrelay configurada")
    
    try:
        # Determine Reply-To based on gym's email
        reply_to = None
        if gym.email:
            reply_to = gym.email
        
        # Prepare HTML if not provided
        if not html_body:
            html_body = f"<div style='font-family: Arial, sans-serif;'>{body.replace(chr(10), '<br>')}</div>"
        
        # Add signature and footer (with no-reply message if no gym email)
        full_body, full_html = _add_gym_signature(gym, body, html_body, add_noreply=not gym.email)
        
        # Prepare sender info
        from_email = config.mailrelay_sender_email
        from_name = config.mailrelay_sender_name or config.system_name
        
        # Mailrelay API v1 - Send email
        api_url = config.mailrelay_api_url.rstrip('/') + '/send_emails'
        
        headers = {
            'X-Auth-Token': config.mailrelay_api_key,
            'Content-Type': 'application/json'
        }
        
        # Build payload for Mailrelay
        payload = {
            'from': {
                'email': from_email,
                'name': from_name
            },
            'to': [{'email': email} for email in to_emails],
            'subject': subject,
            'html_part': full_html,
            'text_part': full_body
        }
        
        # Add Reply-To if gym has email
        if reply_to:
            payload['reply_to'] = {'email': reply_to}
        
        response = requests.post(api_url, json=payload, headers=headers, timeout=30)
        
        if response.status_code in [200, 201, 202]:
            logger.info(f"Email sent via Mailrelay for gym {gym.name} -> {to_emails}")
            return True
        else:
            error_msg = response.json().get('message', response.text)
            logger.error(f"Mailrelay error: {response.status_code} - {error_msg}")
            raise MailrelayError(f"Error de Mailrelay: {error_msg}")
            
    except requests.RequestException as e:
        logger.error(f"Mailrelay connection error: {str(e)}")
        raise MailrelayError(f"Error de conexión con Mailrelay: {str(e)}")


def _add_gym_signature(
    gym,
    body: str,
    html_body: str,
    add_noreply: bool = False
) -> Tuple[str, str]:
    """
    Add gym's signature and footer to the email body.
    If add_noreply is True, adds the no-reply message from config.
    """
    full_body = body
    full_html = html_body
    
    # Add no-reply message if needed
    if add_noreply:
        config = _get_billing_config()
        noreply_msg = config.mailrelay_noreply_message
        if noreply_msg:
            full_body = f"{noreply_msg}\n\n{full_body}"
            full_html = f"<p style='color: #6b7280; font-size: 12px; font-style: italic;'>{noreply_msg}</p>{full_html}"
    
    # Add signature
    if gym.email_signature or gym.email_signature_logo:
        signature_html = "<div style='margin-top: 30px; padding-top: 20px; border-top: 1px solid #e5e7eb;'>"
        
        if gym.email_signature_logo:
            signature_html += f"<img src='{gym.email_signature_logo.url}' alt='{gym.commercial_name or gym.name}' style='max-height: 80px; width: auto; margin-bottom: 10px;'><br>"
        
        if gym.email_signature:
            signature_html += f"<div style='color: #374151; font-size: 13px;'>{gym.email_signature.replace(chr(10), '<br>')}</div>"
            full_body += f"\n\n---\n{gym.email_signature}"
        
        signature_html += "</div>"
        full_html += signature_html
    
    # Add footer
    if gym.email_footer:
        full_body += f"\n\n{gym.email_footer}"
        full_html += f"<div style='font-size: 11px; color: #6b7280; margin-top: 30px; padding-top: 20px; border-top: 1px solid #e5e7eb;'>{gym.email_footer.replace(chr(10), '<br>')}</div>"
    
    return full_body, full_html


def send_email(
    gym,
    to: Union[str, List[str]],
    subject: str,
    body: str,
    html_body: Optional[str] = None,
    attachments: Optional[List[Tuple]] = None,
    force_mailrelay: bool = False
) -> bool:
    """
    Send an email using the appropriate method for the gym.
    
    Priority:
    1. If gym has SMTP configured (and not force_mailrelay) → Use gym's SMTP
    2. If gym's plan includes transactional email → Use Mailrelay
    3. Otherwise → Raise NoEmailConfigurationError
    
    Args:
        gym: The gym instance
        to: Email address(es) to send to
        subject: Email subject
        body: Plain text body
        html_body: Optional HTML body
        attachments: Optional list of (filename, content, mimetype) tuples
        force_mailrelay: Force using Mailrelay even if SMTP is configured
    
    Returns:
        bool: True if email was sent successfully
    
    Raises:
        NoEmailConfigurationError: If no email method is available
        EmailLimitExceededError: If email limits are exceeded
        EmailServiceError: If sending fails
    """
    # Normalize to list
    if isinstance(to, str):
        to_emails = [to]
    else:
        to_emails = list(to)
    
    # Check if gym has SMTP and we're not forcing Mailrelay
    if _has_smtp_configured(gym) and not force_mailrelay:
        return _send_via_gym_smtp(
            gym=gym,
            to_emails=to_emails,
            subject=subject,
            body=body,
            html_body=html_body,
            attachments=attachments
        )
    
    # Try Mailrelay
    subscription = _get_gym_subscription(gym)
    
    # Check if plan includes transactional email
    if not subscription or not subscription.plan.module_transactional_email:
        # Check if Mailrelay is configured at platform level
        config = _get_billing_config()
        if not config.mailrelay_enabled:
            raise NoEmailConfigurationError(
                "El gimnasio no tiene SMTP configurado y el plan no incluye email transaccional"
            )
        raise NoEmailConfigurationError(
            "El plan del gimnasio no incluye el servicio de email transaccional"
        )
    
    # Check limits
    can_send, error_msg = _check_email_limits(gym, subscription)
    if not can_send:
        raise EmailLimitExceededError(error_msg)
    
    # Send via Mailrelay
    result = _send_via_mailrelay(
        gym=gym,
        to_emails=to_emails,
        subject=subject,
        body=body,
        html_body=html_body
    )
    
    # Increment usage counter on success
    if result:
        _increment_email_usage(gym)
    
    return result


def send_template_email(
    gym,
    to: Union[str, List[str]],
    subject: str,
    template: str,
    context: dict,
    attachments: Optional[List[Tuple]] = None,
    force_mailrelay: bool = False
) -> bool:
    """
    Send an email using a Django template.
    
    Args:
        gym: The gym instance
        to: Email address(es) to send to
        subject: Email subject
        template: Path to the template (e.g., 'emails/welcome.html')
        context: Dictionary with template context
        attachments: Optional list of (filename, content, mimetype) tuples
        force_mailrelay: Force using Mailrelay even if SMTP is configured
    
    Returns:
        bool: True if email was sent successfully
    """
    # Add gym to context
    context['gym'] = gym
    context['gym_name'] = gym.commercial_name or gym.name
    
    # Render template
    html_body = render_to_string(template, context)
    text_body = strip_tags(html_body)
    
    return send_email(
        gym=gym,
        to=to,
        subject=subject,
        body=text_body,
        html_body=html_body,
        attachments=attachments,
        force_mailrelay=force_mailrelay
    )


def can_send_email(gym) -> Tuple[bool, str, str]:
    """
    Check if a gym can send emails and which method will be used.
    
    Returns:
        Tuple of (can_send, method, message)
        method: 'smtp', 'mailrelay', or None
    """
    # Check SMTP first
    if _has_smtp_configured(gym):
        return True, 'smtp', 'SMTP del gimnasio configurado'
    
    # Check Mailrelay
    config = _get_billing_config()
    if not config.mailrelay_enabled:
        return False, None, 'No hay servicio de email disponible'
    
    subscription = _get_gym_subscription(gym)
    if not subscription:
        return False, None, 'El gimnasio no tiene suscripción activa'
    
    if not subscription.plan.module_transactional_email:
        return False, None, 'El plan no incluye email transaccional'
    
    # Check limits
    can_send, error_msg = _check_email_limits(gym, subscription)
    if not can_send:
        return False, 'mailrelay', error_msg
    
    return True, 'mailrelay', 'Servicio de email transaccional disponible'


def get_email_usage_stats(gym) -> dict:
    """
    Get email usage statistics for a gym.
    
    Returns:
        dict with:
        - method: 'smtp' or 'mailrelay'
        - daily_sent: emails sent today
        - daily_limit: daily limit (None = unlimited)
        - monthly_sent: emails sent this month
        - monthly_limit: monthly limit (None = unlimited)
        - daily_remaining: remaining emails today (None = unlimited)
        - monthly_remaining: remaining emails this month (None = unlimited)
    """
    from saas_billing.models import GymEmailUsage
    
    stats = {
        'method': 'smtp' if _has_smtp_configured(gym) else 'mailrelay',
        'daily_sent': GymEmailUsage.get_daily_count(gym),
        'monthly_sent': GymEmailUsage.get_monthly_count(gym),
        'daily_limit': None,
        'monthly_limit': None,
        'daily_remaining': None,
        'monthly_remaining': None,
    }
    
    # Get limits from plan
    subscription = _get_gym_subscription(gym)
    if subscription and subscription.plan.module_transactional_email:
        plan = subscription.plan
        
        if plan.transactional_email_limit_daily:
            stats['daily_limit'] = plan.transactional_email_limit_daily
            stats['daily_remaining'] = max(0, plan.transactional_email_limit_daily - stats['daily_sent'])
        
        if plan.transactional_email_limit_monthly:
            stats['monthly_limit'] = plan.transactional_email_limit_monthly
            stats['monthly_remaining'] = max(0, plan.transactional_email_limit_monthly - stats['monthly_sent'])
    
    return stats
