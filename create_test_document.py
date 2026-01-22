"""
Script para crear documento de prueba en el portal
"""
import os
import django

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'config.settings')
django.setup()

from clients.models import Client, ClientDocument
from django.utils import timezone

# Obtener el primer cliente que tenga un user asociado
client = Client.objects.filter(user__isnull=False).first()

if client:
    # Crear documento de prueba
    doc = ClientDocument.objects.create(
        client=client,
        name="Contrato de Adhesión 2026",
        document_type='CONTRACT',
        content="""
        <div style="font-family: Arial, sans-serif; padding: 20px; max-width: 800px;">
            <h1 style="color: #1e40af; text-align: center;">CONTRATO DE ADHESIÓN</h1>
            <h2 style="color: #3b82f6;">GIMNASIO {}</h2>
            
            <p style="line-height: 1.6; margin-top: 20px;">
                <strong>ENTRE:</strong> El gimnasio {} (en adelante "EL GIMNASIO"), 
                y <strong>{} {}</strong> (en adelante "EL CLIENTE").
            </p>
            
            <h3 style="color: #1e40af; margin-top: 30px;">CLÁUSULAS:</h3>
            
            <p style="line-height: 1.6;"><strong>PRIMERA - OBJETO:</strong> 
            El presente contrato tiene por objeto regular la prestación de servicios deportivos 
            por parte de EL GIMNASIO a EL CLIENTE.</p>
            
            <p style="line-height: 1.6;"><strong>SEGUNDA - DURACIÓN:</strong> 
            Este contrato tendrá una duración de 12 meses desde la fecha de firma, 
            renovable automáticamente por períodos iguales.</p>
            
            <p style="line-height: 1.6;"><strong>TERCERA - OBLIGACIONES DEL CLIENTE:</strong></p>
            <ul style="line-height: 1.8;">
                <li>Respetar las normas de uso de las instalaciones</li>
                <li>Abonar puntualmente las cuotas mensuales</li>
                <li>Utilizar adecuadamente el equipamiento</li>
                <li>Respetar los horarios establecidos</li>
            </ul>
            
            <p style="line-height: 1.6;"><strong>CUARTA - OBLIGACIONES DEL GIMNASIO:</strong></p>
            <ul style="line-height: 1.8;">
                <li>Mantener las instalaciones en perfecto estado</li>
                <li>Proporcionar asesoramiento profesional</li>
                <li>Garantizar la seguridad de los usuarios</li>
                <li>Ofrecer los servicios contratados</li>
            </ul>
            
            <p style="line-height: 1.6;"><strong>QUINTA - PROTECCIÓN DE DATOS:</strong> 
            Los datos personales serán tratados conforme al RGPD y la LOPD-GDD, pudiendo ser utilizados 
            para la gestión de la relación contractual y envío de comunicaciones comerciales.</p>
            
            <p style="line-height: 1.6; margin-top: 30px;">
                He leído y acepto los términos y condiciones del presente contrato.
            </p>
            
            <p style="margin-top: 40px; text-align: right;">
                <strong>Fecha:</strong> {} <br>
                <strong>Firma del Cliente:</strong> _____________________
            </p>
        </div>
        """.format(
            client.gym.name,
            client.gym.name,
            client.first_name,
            client.last_name,
            timezone.now().strftime("%d/%m/%Y")
        ),
        requires_signature=True,
        status='PENDING',
        sent_at=timezone.now(),
    )
    
    print(f"✅ Documento creado: {doc.name}")
    print(f"   Cliente: {client.first_name} {client.last_name}")
    print(f"   Email: {client.email}")
    print(f"   ID: {doc.id}")
    print(f"\n🔗 Ver en portal: http://localhost:8001/portal/documents/{doc.id}/")
else:
    print("❌ No se encontró ningún cliente con usuario asociado")
