"""
Servicios de Control de Acceso
==============================
Lógica de negocio para validación y registro de accesos.
"""

from django.utils import timezone
from django.db import transaction
from datetime import timedelta
from typing import Optional, Tuple, Dict, Any

from .models import (
    AccessDevice, AccessZone, AccessLog, AccessAlert,
    ClientAccessCredential, AccessSchedule
)
from clients.models import Client, ClientMembership


class AccessValidationResult:
    """Resultado de una validación de acceso."""
    
    def __init__(
        self,
        granted: bool,
        client: Optional[Client] = None,
        denial_reason: str = '',
        message: str = '',
        details: Dict[str, Any] = None
    ):
        self.granted = granted
        self.client = client
        self.denial_reason = denial_reason
        self.message = message
        self.details = details or {}
    
    def to_dict(self):
        return {
            'granted': self.granted,
            'client_id': self.client.id if self.client else None,
            'client_name': self.client.full_name if self.client else None,
            'denial_reason': self.denial_reason,
            'message': self.message,
            'details': self.details
        }


class AccessControlService:
    """
    Servicio principal de control de acceso.
    Maneja la validación y registro de entradas/salidas.
    """
    
    def __init__(self, gym):
        self.gym = gym
    
    def validate_access(
        self,
        credential_type: str,
        credential_value: str,
        device: Optional[AccessDevice] = None,
        direction: str = 'ENTRY'
    ) -> AccessValidationResult:
        """
        Valida si un cliente puede acceder.
        
        Args:
            credential_type: Tipo de credencial (RFID, QR_DYNAMIC, PIN, etc.)
            credential_value: Valor de la credencial
            device: Dispositivo de acceso (opcional)
            direction: 'ENTRY' o 'EXIT'
        
        Returns:
            AccessValidationResult con el resultado de la validación
        """
        # 1. Buscar la credencial
        credential = self._find_credential(credential_type, credential_value)
        if not credential:
            return AccessValidationResult(
                granted=False,
                denial_reason='INVALID_CREDENTIAL',
                message='Credencial no reconocida'
            )
        
        client = credential.client
        
        # 2. Verificar que la credencial está activa y vigente
        if not credential.is_valid:
            return AccessValidationResult(
                granted=False,
                client=client,
                denial_reason='CREDENTIAL_EXPIRED',
                message='Credencial expirada o inactiva'
            )
        
        # 3. Verificar estado del cliente
        if client.status == 'BLOCKED':
            return AccessValidationResult(
                granted=False,
                client=client,
                denial_reason='ACCOUNT_BLOCKED',
                message='Cuenta bloqueada'
            )
        
        # 4. Verificar membresía activa
        membership_check = self._check_membership(client)
        if not membership_check['valid']:
            return AccessValidationResult(
                granted=False,
                client=client,
                denial_reason=membership_check['reason'],
                message=membership_check['message']
            )
        
        # 5. Verificar horario de acceso (si el plan tiene restricciones)
        schedule_check = self._check_schedule(client, membership_check['membership'])
        if not schedule_check['allowed']:
            return AccessValidationResult(
                granted=False,
                client=client,
                denial_reason='SCHEDULE_RESTRICTED',
                message=schedule_check['message']
            )
        
        # 6. Verificar zona de acceso (si el dispositivo tiene zona asignada)
        if device and device.zone:
            zone_check = self._check_zone_access(client, device.zone, membership_check['membership'])
            if not zone_check['allowed']:
                return AccessValidationResult(
                    granted=False,
                    client=client,
                    denial_reason=zone_check['reason'],
                    message=zone_check['message']
                )
        
        # 7. Todo OK - Acceso concedido
        return AccessValidationResult(
            granted=True,
            client=client,
            message='Acceso concedido',
            details={
                'membership_name': membership_check['membership'].name,
                'membership_end': membership_check['membership'].end_date.isoformat() if membership_check['membership'].end_date else None,
                'zone': device.zone.name if device and device.zone else None,
            }
        )
    
    def _find_credential(
        self,
        credential_type: str,
        credential_value: str
    ) -> Optional[ClientAccessCredential]:
        """Busca una credencial en la base de datos."""
        try:
            return ClientAccessCredential.objects.select_related('client').get(
                client__gym=self.gym,
                credential_type=credential_type,
                credential_value=credential_value,
                is_active=True
            )
        except ClientAccessCredential.DoesNotExist:
            return None
    
    def _check_membership(self, client: Client) -> Dict[str, Any]:
        """Verifica que el cliente tenga membresía activa."""
        today = timezone.now().date()
        
        # Buscar membresía activa
        membership = ClientMembership.objects.filter(
            client=client,
            gym=self.gym,
            status='ACTIVE',
            start_date__lte=today,
        ).filter(
            # end_date es None (sin fecha fin) o mayor/igual a hoy
            models.Q(end_date__isnull=True) | models.Q(end_date__gte=today)
        ).first()
        
        if not membership:
            # Verificar si tiene membresía expirada
            expired = ClientMembership.objects.filter(
                client=client,
                gym=self.gym,
                end_date__lt=today
            ).exists()
            
            if expired:
                return {
                    'valid': False,
                    'reason': 'MEMBERSHIP_EXPIRED',
                    'message': 'Tu membresía ha expirado',
                    'membership': None
                }
            
            return {
                'valid': False,
                'reason': 'NO_MEMBERSHIP',
                'message': 'No tienes una membresía activa',
                'membership': None
            }
        
        return {
            'valid': True,
            'reason': '',
            'message': '',
            'membership': membership
        }
    
    def _check_schedule(
        self,
        client: Client,
        membership: ClientMembership
    ) -> Dict[str, Any]:
        """Verifica si el cliente puede acceder en el horario actual."""
        if not membership.plan:
            return {'allowed': True, 'message': ''}
        
        # Obtener horarios asociados al plan
        schedules = AccessSchedule.objects.filter(
            gym=self.gym,
            membership_plans=membership.plan,
            is_active=True
        )
        
        # Si no hay horarios definidos, permitir siempre
        if not schedules.exists():
            return {'allowed': True, 'message': ''}
        
        # Verificar si algún horario permite el acceso ahora
        for schedule in schedules:
            if schedule.is_access_allowed_now():
                return {'allowed': True, 'message': ''}
        
        return {
            'allowed': False,
            'message': 'Tu plan no permite acceso en este horario'
        }
    
    def _check_zone_access(
        self,
        client: Client,
        zone: AccessZone,
        membership: ClientMembership
    ) -> Dict[str, Any]:
        """Verifica si el cliente puede acceder a la zona."""
        # Si la zona no requiere membresía específica, permitir
        if not zone.requires_specific_membership:
            # Solo verificar aforo
            return self._check_zone_capacity(zone)
        
        # Verificar si el plan permite acceso a esta zona
        if membership.plan and zone.allowed_membership_plans.filter(id=membership.plan.id).exists():
            return self._check_zone_capacity(zone)
        
        return {
            'allowed': False,
            'reason': 'ZONE_NOT_ALLOWED',
            'message': f'Tu plan no incluye acceso a {zone.name}'
        }
    
    def _check_zone_capacity(self, zone: AccessZone) -> Dict[str, Any]:
        """Verifica el aforo de la zona."""
        if not zone.max_capacity:
            return {'allowed': True, 'reason': '', 'message': ''}
        
        current_occupancy = zone.get_current_occupancy()
        if current_occupancy >= zone.max_capacity:
            return {
                'allowed': False,
                'reason': 'CAPACITY_EXCEEDED',
                'message': f'La zona {zone.name} está completa'
            }
        
        return {'allowed': True, 'reason': '', 'message': ''}
    
    @transaction.atomic
    def register_access(
        self,
        validation_result: AccessValidationResult,
        device: Optional[AccessDevice],
        direction: str,
        credential_type: str = '',
        credential_value: str = '',
        raw_data: Dict = None,
        processed_by=None
    ) -> AccessLog:
        """
        Registra un intento de acceso en el log.
        
        Args:
            validation_result: Resultado de la validación
            device: Dispositivo de acceso
            direction: 'ENTRY' o 'EXIT'
            credential_type: Tipo de credencial usada
            credential_value: Valor de la credencial (se enmascara)
            raw_data: Datos crudos del dispositivo
            processed_by: Usuario que procesó (si es manual)
        
        Returns:
            AccessLog creado
        """
        # Enmascarar credencial
        masked_value = self._mask_credential(credential_value)
        
        # Crear el log
        log = AccessLog.objects.create(
            gym=self.gym,
            client=validation_result.client,
            device=device,
            direction=direction,
            status='GRANTED' if validation_result.granted else 'DENIED',
            denial_reason=validation_result.denial_reason,
            credential_type=credential_type,
            credential_value_masked=masked_value,
            raw_data=raw_data or {},
            processed_by=processed_by,
            notes=validation_result.message
        )
        
        # Crear alerta si fue denegado
        if not validation_result.granted:
            self._create_denial_alert(log, validation_result)
        
        # Verificar aforo después de entrada
        if validation_result.granted and direction == 'ENTRY' and device and device.zone:
            self._check_capacity_alert(device.zone)
        
        return log
    
    def _mask_credential(self, value: str) -> str:
        """Enmascara una credencial para el log."""
        if not value:
            return ''
        if len(value) <= 4:
            return '*' * len(value)
        return '*' * (len(value) - 4) + value[-4:]
    
    def _create_denial_alert(
        self,
        log: AccessLog,
        result: AccessValidationResult
    ):
        """Crea una alerta por acceso denegado."""
        AccessAlert.objects.create(
            gym=self.gym,
            alert_type='DENIED_ACCESS',
            severity='MEDIUM',
            title=f'Acceso denegado: {result.denial_reason}',
            message=result.message,
            client=result.client,
            device=log.device,
            access_log=log
        )
    
    def _check_capacity_alert(self, zone: AccessZone):
        """Verifica y crea alertas de aforo."""
        if not zone.max_capacity:
            return
        
        occupancy = zone.get_current_occupancy()
        percentage = (occupancy / zone.max_capacity) * 100
        
        # Alerta al 90%
        if 90 <= percentage < 100:
            AccessAlert.objects.get_or_create(
                gym=self.gym,
                alert_type='CAPACITY_WARNING',
                is_resolved=False,
                defaults={
                    'severity': 'MEDIUM',
                    'title': f'Aforo al {int(percentage)}% en {zone.name}',
                    'message': f'La zona {zone.name} está al {int(percentage)}% de su capacidad ({occupancy}/{zone.max_capacity})'
                }
            )
        # Alerta al 100%
        elif percentage >= 100:
            AccessAlert.objects.get_or_create(
                gym=self.gym,
                alert_type='CAPACITY_EXCEEDED',
                is_resolved=False,
                defaults={
                    'severity': 'HIGH',
                    'title': f'Aforo completo en {zone.name}',
                    'message': f'La zona {zone.name} ha alcanzado su capacidad máxima ({zone.max_capacity})'
                }
            )
    
    def get_current_occupancy(self, zone: Optional[AccessZone] = None) -> Dict[str, Any]:
        """
        Obtiene el aforo actual del gimnasio o de una zona específica.
        """
        twelve_hours_ago = timezone.now() - timedelta(hours=12)
        
        base_query = AccessLog.objects.filter(
            gym=self.gym,
            timestamp__gte=twelve_hours_ago,
            status='GRANTED'
        )
        
        if zone:
            base_query = base_query.filter(device__zone=zone)
        
        entries = set(base_query.filter(direction='ENTRY').values_list('client_id', flat=True))
        exits = set(base_query.filter(direction='EXIT').values_list('client_id', flat=True))
        
        inside_clients = entries - exits
        
        return {
            'current_count': len(inside_clients),
            'client_ids': list(inside_clients),
            'zone': zone.name if zone else 'General',
            'timestamp': timezone.now().isoformat()
        }
    
    def get_clients_inside(self) -> list:
        """Obtiene lista de clientes actualmente dentro del gimnasio."""
        occupancy = self.get_current_occupancy()
        
        if not occupancy['client_ids']:
            return []
        
        from clients.models import Client
        return list(Client.objects.filter(
            id__in=occupancy['client_ids']
        ).values('id', 'first_name', 'last_name', 'email', 'photo'))
    
    def validate_qr_token(self, token: str, device: Optional[AccessDevice] = None) -> AccessValidationResult:
        """
        Valida un token QR dinámico de la app móvil.
        """
        from clients.models import Client
        
        try:
            # Buscar cliente por token QR activo
            client = Client.objects.get(
                gym=self.gym,
                qr_token=token,
                qr_token_expires__gt=timezone.now()
            )
            
            # Usar la validación estándar
            # Crear credencial temporal para validación
            return self.validate_access(
                credential_type='QR_DYNAMIC',
                credential_value=token,
                device=device,
                direction='ENTRY'
            )
        except Client.DoesNotExist:
            return AccessValidationResult(
                granted=False,
                denial_reason='INVALID_CREDENTIAL',
                message='QR inválido o expirado'
            )


# Importar models para las queries
from django.db import models
