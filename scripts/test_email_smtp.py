"""
Script de prueba para envío de emails usando la configuración SMTP del gimnasio
"""
import os
import django

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'config.settings')
django.setup()

from django.core.mail import EmailMessage
from django.conf import settings
from organizations.models import Gym
from clients.models import Client

def test_email_with_gym_smtp():
    """Envía un email de prueba usando la configuración SMTP del gimnasio"""
    
    # Obtener gimnasio Qombo Arganzuela
    try:
        gym = Gym.objects.get(name__icontains='Qombo Arganzuela')
        print(f"✓ Gimnasio encontrado: {gym.name}")
    except Gym.DoesNotExist:
        print("❌ No se encontró el gimnasio Qombo Arganzuela")
        return
    
    # Verificar configuración SMTP
    if not gym.smtp_host:
        print("❌ El gimnasio no tiene configuración SMTP")
        return
    
    print(f"\n📧 Configuración SMTP:")
    print(f"  Host: {gym.smtp_host}")
    print(f"  Port: {gym.smtp_port}")
    print(f"  Username: {gym.smtp_username}")
    print(f"  Use TLS: {gym.smtp_use_tls}")
    print(f"  From: {gym.smtp_from_email}")
    
    # Buscar o crear cliente con el email gestión@hotmail.com
    email_prueba = "gestión@hotmail.com"
    
    try:
        cliente = Client.objects.get(gym=gym, email=email_prueba)
        print(f"\n✓ Cliente encontrado: {cliente.name} {cliente.last_name}")
    except Client.DoesNotExist:
        # Crear cliente de prueba
        cliente = Client.objects.create(
            gym=gym,
            name="Cliente",
            last_name="Prueba SMTP",
            email=email_prueba,
            phone="600000000"
        )
        print(f"\n✓ Cliente creado: {cliente.name} {cliente.last_name}")
    
    # Configurar el backend de email temporalmente con la config del gimnasio
    from django.core.mail import get_connection
    
    connection = get_connection(
        backend='django.core.mail.backends.smtp.EmailBackend',
        host=gym.smtp_host,
        port=gym.smtp_port,
        username=gym.smtp_username,
        password=gym.smtp_password,
        use_tls=gym.smtp_use_tls,
        use_ssl=gym.smtp_use_ssl,
        fail_silently=False,
    )
    
    # Crear y enviar email
    subject = f"Prueba de Email - {gym.commercial_name or gym.name}"
    message = f"""
    Hola {cliente.name},
    
    Este es un email de prueba desde el sistema CRM de {gym.commercial_name or gym.name}.
    
    Si recibes este mensaje, significa que la configuración SMTP está funcionando correctamente! 🎉
    
    Detalles de la prueba:
    - Gimnasio: {gym.name}
    - Fecha: {django.utils.timezone.now().strftime('%d/%m/%Y %H:%M')}
    - Sistema: New CRM
    
    Saludos,
    El equipo de {gym.commercial_name or gym.name}
    """
    
    email = EmailMessage(
        subject=subject,
        body=message,
        from_email=gym.smtp_from_email or gym.smtp_username,
        to=[cliente.email],
        connection=connection
    )
    
    try:
        print(f"\n📤 Enviando email a {cliente.email}...")
        email.send()
        print(f"✅ Email enviado correctamente!")
        print(f"\n📬 Revisa la bandeja de entrada de {cliente.email}")
        
    except Exception as e:
        print(f"\n❌ Error al enviar email:")
        print(f"   {type(e).__name__}: {str(e)}")
        import traceback
        print("\n" + traceback.format_exc())

if __name__ == "__main__":
    print("=" * 60)
    print("TEST DE ENVÍO DE EMAIL CON SMTP DEL GIMNASIO")
    print("=" * 60)
    test_email_with_gym_smtp()
    print("\n" + "=" * 60)
