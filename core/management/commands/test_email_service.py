"""
Management command to test the unified email service.

Usage:
    python manage.py test_email_service --gym-id=1 --to=test@example.com
    python manage.py test_email_service --gym-id=1 --to=test@example.com --force-mailrelay
"""
from django.core.management.base import BaseCommand, CommandError
from organizations.models import Gym


class Command(BaseCommand):
    help = 'Test the unified email service for a gym'

    def add_arguments(self, parser):
        parser.add_argument(
            '--gym-id',
            type=int,
            required=True,
            help='ID del gimnasio para probar'
        )
        parser.add_argument(
            '--to',
            type=str,
            required=True,
            help='Email destinatario para la prueba'
        )
        parser.add_argument(
            '--force-mailrelay',
            action='store_true',
            help='Forzar uso de Mailrelay aunque tenga SMTP configurado'
        )

    def handle(self, *args, **options):
        from core.email_service import (
            send_email, 
            can_send_email, 
            get_email_usage_stats,
            NoEmailConfigurationError,
            EmailLimitExceededError,
            EmailServiceError
        )
        
        gym_id = options['gym_id']
        to_email = options['to']
        force_mailrelay = options['force_mailrelay']
        
        # Get gym
        try:
            gym = Gym.objects.get(id=gym_id)
        except Gym.DoesNotExist:
            raise CommandError(f'Gimnasio con ID {gym_id} no encontrado')
        
        self.stdout.write(self.style.NOTICE(f'\n{"="*60}'))
        self.stdout.write(self.style.NOTICE(f'TEST DE EMAIL SERVICE'))
        self.stdout.write(self.style.NOTICE(f'{"="*60}\n'))
        
        # 1. Check configuration
        self.stdout.write(self.style.HTTP_INFO('1. Verificando configuración...'))
        
        can_send, method, message = can_send_email(gym)
        
        self.stdout.write(f'   Gimnasio: {gym.name}')
        self.stdout.write(f'   SMTP configurado: {"✅ Sí" if gym.smtp_host else "❌ No"}')
        if gym.smtp_host:
            self.stdout.write(f'   - Host: {gym.smtp_host}:{gym.smtp_port}')
            self.stdout.write(f'   - Usuario: {gym.smtp_username}')
        
        self.stdout.write(f'   Puede enviar: {"✅ Sí" if can_send else "❌ No"}')
        self.stdout.write(f'   Método: {method or "Ninguno"}')
        self.stdout.write(f'   Mensaje: {message}')
        
        # 2. Show usage stats
        self.stdout.write(self.style.HTTP_INFO('\n2. Estadísticas de uso...'))
        stats = get_email_usage_stats(gym)
        self.stdout.write(f'   Emails hoy: {stats["daily_sent"]} / {stats["daily_limit"] or "∞"}')
        self.stdout.write(f'   Emails este mes: {stats["monthly_sent"]} / {stats["monthly_limit"] or "∞"}')
        
        if not can_send and not force_mailrelay:
            self.stdout.write(self.style.ERROR(f'\n❌ No se puede enviar email: {message}'))
            return
        
        # 3. Send test email
        self.stdout.write(self.style.HTTP_INFO(f'\n3. Enviando email de prueba a {to_email}...'))
        
        if force_mailrelay:
            self.stdout.write(self.style.WARNING('   (Forzando uso de Mailrelay)'))
        
        try:
            result = send_email(
                gym=gym,
                to=to_email,
                subject=f'🧪 Test Email Service - {gym.name}',
                body=f'''Hola!

Este es un email de prueba del servicio de email transaccional.

Detalles:
- Gimnasio: {gym.name}
- Método: {"Mailrelay (forzado)" if force_mailrelay else method}
- Fecha: {__import__("django").utils.timezone.now().strftime("%d/%m/%Y %H:%M")}

Si recibes este email, ¡el sistema funciona correctamente!

Saludos,
Sistema CRM
''',
                html_body=f'''
<div style="font-family: Arial, sans-serif; max-width: 600px; margin: 0 auto;">
    <div style="background: linear-gradient(135deg, #667eea 0%, #764ba2 100%); padding: 30px; border-radius: 10px 10px 0 0;">
        <h1 style="color: white; margin: 0;">🧪 Test Email Service</h1>
        <p style="color: rgba(255,255,255,0.8); margin: 10px 0 0;">Verificación del sistema</p>
    </div>
    <div style="background: #f8f9fa; padding: 30px; border-radius: 0 0 10px 10px;">
        <p style="color: #333;">¡Hola!</p>
        <p style="color: #666;">Este es un email de prueba del servicio de email transaccional.</p>
        
        <div style="background: white; padding: 20px; border-radius: 8px; margin: 20px 0; border-left: 4px solid #667eea;">
            <h3 style="margin: 0 0 15px; color: #333;">📋 Detalles:</h3>
            <table style="width: 100%; color: #666;">
                <tr>
                    <td style="padding: 5px 0;"><strong>Gimnasio:</strong></td>
                    <td>{gym.name}</td>
                </tr>
                <tr>
                    <td style="padding: 5px 0;"><strong>Método:</strong></td>
                    <td>{"Mailrelay (forzado)" if force_mailrelay else method}</td>
                </tr>
                <tr>
                    <td style="padding: 5px 0;"><strong>Fecha:</strong></td>
                    <td>{__import__("django").utils.timezone.now().strftime("%d/%m/%Y %H:%M")}</td>
                </tr>
            </table>
        </div>
        
        <div style="background: #d4edda; padding: 15px; border-radius: 8px; text-align: center;">
            <p style="color: #155724; margin: 0; font-weight: bold;">
                ✅ Si recibes este email, ¡el sistema funciona correctamente!
            </p>
        </div>
        
        <p style="color: #999; font-size: 12px; margin-top: 30px; text-align: center;">
            Este es un email de prueba generado automáticamente.
        </p>
    </div>
</div>
''',
                force_mailrelay=force_mailrelay
            )
            
            if result:
                self.stdout.write(self.style.SUCCESS(f'\n✅ ¡Email enviado correctamente!'))
                self.stdout.write(f'   Revisa la bandeja de entrada de {to_email}')
            else:
                self.stdout.write(self.style.WARNING(f'\n⚠️ El envío retornó False'))
                
        except NoEmailConfigurationError as e:
            self.stdout.write(self.style.ERROR(f'\n❌ Error de configuración: {e}'))
        except EmailLimitExceededError as e:
            self.stdout.write(self.style.ERROR(f'\n❌ Límite excedido: {e}'))
        except EmailServiceError as e:
            self.stdout.write(self.style.ERROR(f'\n❌ Error del servicio: {e}'))
        except Exception as e:
            self.stdout.write(self.style.ERROR(f'\n❌ Error inesperado: {e}'))
            import traceback
            traceback.print_exc()
        
        self.stdout.write(self.style.NOTICE(f'\n{"="*60}\n'))
