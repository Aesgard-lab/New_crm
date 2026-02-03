"""
Servicio de reconocimiento facial.
Utiliza la librería face_recognition para detectar y comparar rostros.
"""
import time
import logging
import numpy as np
from io import BytesIO
from typing import Optional, Tuple
from PIL import Image

from django.utils import timezone
from django.core.files.uploadedfile import InMemoryUploadedFile

logger = logging.getLogger(__name__)

# Función para verificar disponibilidad de face_recognition dinámicamente
def check_face_recognition_available():
    """
    Verifica si la librería face_recognition está disponible.
    Se evalúa cada vez que se llama para detectar instalaciones en caliente.
    """
    try:
        import face_recognition
        return True
    except ImportError:
        return False

# Variable global que se puede actualizar
FACE_RECOGNITION_AVAILABLE = check_face_recognition_available()

if not FACE_RECOGNITION_AVAILABLE:
    logger.warning(
        "Módulo de reconocimiento facial no disponible (face_recognition library not installed)"
    )


class FaceRecognitionService:
    """
    Servicio para registrar y verificar rostros de clientes.
    """
    
    def __init__(self, gym=None):
        self.gym = gym
        self._settings = None
    
    @property
    def settings(self):
        """Obtiene la configuración del gym"""
        if self._settings is None and self.gym:
            from .models import FaceRecognitionSettings
            self._settings, _ = FaceRecognitionSettings.objects.get_or_create(
                gym=self.gym
            )
        return self._settings
    
    @property
    def is_available(self) -> bool:
        """Comprueba si el reconocimiento facial está disponible"""
        return FACE_RECOGNITION_AVAILABLE
    
    def _load_image(self, image_file) -> Optional[np.ndarray]:
        """
        Carga una imagen desde un archivo.
        Acepta: InMemoryUploadedFile, BytesIO, path string
        """
        try:
            if isinstance(image_file, (InMemoryUploadedFile, BytesIO)):
                # Leer desde memoria
                image_file.seek(0)
                pil_image = Image.open(image_file)
                # Convertir a RGB si es necesario
                if pil_image.mode != 'RGB':
                    pil_image = pil_image.convert('RGB')
                return np.array(pil_image)
            elif isinstance(image_file, str):
                # Leer desde path
                return face_recognition.load_image_file(image_file)
            elif isinstance(image_file, np.ndarray):
                return image_file
            else:
                # Intentar leer como file-like
                pil_image = Image.open(image_file)
                if pil_image.mode != 'RGB':
                    pil_image = pil_image.convert('RGB')
                return np.array(pil_image)
        except Exception as e:
            logger.error(f"Error cargando imagen: {e}")
            return None
    
    def detect_faces(self, image_file) -> Tuple[int, list]:
        """
        Detecta rostros en una imagen.
        
        Returns:
            (número de caras, lista de ubicaciones)
        """
        if not FACE_RECOGNITION_AVAILABLE:
            return 0, []
        
        image = self._load_image(image_file)
        if image is None:
            return 0, []
        
        face_locations = face_recognition.face_locations(image)
        return len(face_locations), face_locations
    
    def get_face_encoding(self, image_file) -> Optional[np.ndarray]:
        """
        Extrae el encoding facial de una imagen.
        
        Returns:
            Array de 128 dimensiones o None si no se detecta cara
        """
        if not FACE_RECOGNITION_AVAILABLE:
            logger.error("face_recognition no disponible")
            return None
        
        image = self._load_image(image_file)
        if image is None:
            return None
        
        # Detectar caras
        face_locations = face_recognition.face_locations(image)
        
        if len(face_locations) == 0:
            logger.warning("No se detectó ningún rostro en la imagen")
            return None
        
        if len(face_locations) > 1:
            logger.warning(f"Se detectaron {len(face_locations)} rostros, usando el primero")
        
        # Obtener encoding
        encodings = face_recognition.face_encodings(image, face_locations)
        
        if len(encodings) == 0:
            return None
        
        return encodings[0]
    
    def register_face(self, client, image_file, consent: bool = True) -> dict:
        """
        Registra el rostro de un cliente.
        
        Args:
            client: Instancia de Client
            image_file: Archivo de imagen
            consent: Si el cliente dio consentimiento GDPR
        
        Returns:
            {
                'success': bool,
                'error': str (si hay error),
                'quality_score': float
            }
        """
        from .models import ClientFaceEncoding
        
        if not FACE_RECOGNITION_AVAILABLE:
            return {
                'success': False,
                'error': 'El reconocimiento facial no está disponible en el servidor'
            }
        
        # Obtener encoding
        encoding = self.get_face_encoding(image_file)
        
        if encoding is None:
            return {
                'success': False,
                'error': 'No se detectó un rostro válido en la imagen'
            }
        
        # Calcular calidad (basado en la varianza del encoding)
        quality_score = min(1.0, np.std(encoding) * 5)
        
        # Guardar o actualizar
        face_encoding, created = ClientFaceEncoding.objects.update_or_create(
            client=client,
            defaults={
                'encoding': encoding.tobytes(),
                'consent_given': consent,
                'consent_date': timezone.now() if consent else None,
                'quality_score': quality_score,
            }
        )
        
        return {
            'success': True,
            'created': created,
            'quality_score': quality_score
        }
    
    def register_from_client_photo(self, client, consent: bool = True) -> dict:
        """
        Registra el rostro desde la foto de perfil existente del cliente.
        
        Args:
            client: Instancia de Client
            consent: Si el cliente dio consentimiento GDPR
        
        Returns:
            {
                'success': bool,
                'error': str (si hay error),
                'quality_score': float
            }
        """
        if not client.photo:
            return {
                'success': False,
                'error': 'El cliente no tiene foto de perfil'
            }
        
        try:
            # Abrir la foto del cliente
            photo_path = client.photo.path
            return self.register_face(client, photo_path, consent=consent)
        except Exception as e:
            logger.error(f"Error registrando rostro desde foto del cliente: {e}")
            return {
                'success': False,
                'error': f'Error al procesar la foto: {str(e)}'
            }
    
    def do_session_checkin(self, client, session, confidence: float = None) -> dict:
        """
        Realiza el check-in de un cliente a una sesión de actividad usando reconocimiento facial.
        
        Args:
            client: Cliente que hace check-in
            session: ActivitySession
            confidence: Nivel de confianza del reconocimiento
        
        Returns:
            {
                'success': bool,
                'error': str (si hay error),
                'checkin': SessionCheckin (si éxito)
            }
        """
        from activities.models import SessionCheckin, ActivitySessionBooking
        
        # Verificar si el cliente tiene reserva para esta sesión
        booking = ActivitySessionBooking.objects.filter(
            client=client,
            session=session,
            status='CONFIRMED'
        ).first()
        
        # Si no tiene reserva pero la sesión permite walk-ins, crear registro
        if not booking:
            # Verificar si hay espacio disponible
            if session.booked_count >= session.capacity:
                return {
                    'success': False,
                    'error': 'La sesión está completa'
                }
        
        # Verificar si ya tiene check-in
        existing = SessionCheckin.objects.filter(
            session=session,
            client=client
        ).first()
        
        if existing:
            return {
                'success': False,
                'error': 'El cliente ya tiene check-in en esta sesión',
                'checkin': existing
            }
        
        # Crear check-in
        checkin = SessionCheckin.objects.create(
            session=session,
            client=client,
            method='FACE'
        )
        
        # Si tenía reserva, marcar asistencia correctamente
        if booking:
            booking.mark_attendance('ATTENDED')
        
        # Registrar en el log
        self._log_attempt(
            result='success',
            client=client,
            confidence=confidence,
            activity_session=session
        )
        
        return {
            'success': True,
            'checkin': checkin,
            'had_booking': booking is not None
        }
    
    def verify_face(self, image_file, client=None) -> dict:
        """
        Verifica un rostro contra la base de datos.
        
        Args:
            image_file: Imagen a verificar
            client: (opcional) Si se especifica, solo verifica contra ese cliente
        
        Returns:
            {
                'success': bool,
                'client': Client o None,
                'confidence': float,
                'error': str (si hay error)
            }
        """
        from .models import ClientFaceEncoding, FaceRecognitionLog
        
        start_time = time.time()
        
        if not FACE_RECOGNITION_AVAILABLE:
            return {
                'success': False,
                'error': 'Reconocimiento facial no disponible',
                'client': None
            }
        
        # Obtener encoding de la imagen
        unknown_encoding = self.get_face_encoding(image_file)
        
        if unknown_encoding is None:
            self._log_attempt(
                result=FaceRecognitionLog.NO_FACE,
                processing_time=int((time.time() - start_time) * 1000)
            )
            return {
                'success': False,
                'error': 'No se detectó rostro',
                'client': None
            }
        
        # Obtener encodings de la base de datos
        if client:
            # Verificar solo contra un cliente específico
            face_encodings = ClientFaceEncoding.objects.filter(client=client)
        elif self.gym:
            # Verificar contra todos los clientes del gym
            face_encodings = ClientFaceEncoding.objects.filter(
                client__gym=self.gym,
                client__status='active'
            ).select_related('client')
        else:
            return {
                'success': False,
                'error': 'No se especificó gym ni cliente',
                'client': None
            }
        
        # Comparar con cada encoding
        threshold = self.settings.confidence_threshold if self.settings else 0.6
        best_match = None
        best_confidence = 0
        
        for face_encoding in face_encodings:
            known_encoding = np.frombuffer(face_encoding.encoding, dtype=np.float64)
            
            # Calcular distancia (menor = más parecido)
            distance = face_recognition.face_distance([known_encoding], unknown_encoding)[0]
            confidence = 1 - distance
            
            if confidence > best_confidence:
                best_confidence = confidence
                best_match = face_encoding
        
        processing_time = int((time.time() - start_time) * 1000)
        
        # Determinar si hay match
        if best_match and best_confidence >= (1 - threshold):
            best_match.mark_used()
            self._log_attempt(
                result=FaceRecognitionLog.SUCCESS,
                client=best_match.client,
                confidence=best_confidence,
                processing_time=processing_time
            )
            return {
                'success': True,
                'client': best_match.client,
                'confidence': best_confidence,
                'processing_time_ms': processing_time
            }
        else:
            self._log_attempt(
                result=FaceRecognitionLog.NO_MATCH,
                confidence=best_confidence,
                processing_time=processing_time
            )
            return {
                'success': False,
                'error': 'No se encontró coincidencia',
                'client': None,
                'best_confidence': best_confidence,
                'processing_time_ms': processing_time
            }
    
    def _log_attempt(self, result: str, client=None, confidence=None, 
                     processing_time=None, error_message='', activity_session=None):
        """Registra un intento de reconocimiento"""
        from .models import FaceRecognitionLog
        
        if not self.gym:
            return
        
        try:
            FaceRecognitionLog.objects.create(
                gym=self.gym,
                client=client,
                result=result,
                confidence=confidence,
                processing_time_ms=processing_time,
                error_message=error_message,
                activity_session=activity_session
            )
        except Exception as e:
            logger.error(f"Error guardando log de reconocimiento: {e}")
    
    def delete_face_data(self, client) -> bool:
        """
        Elimina los datos faciales de un cliente (GDPR).
        """
        from .models import ClientFaceEncoding
        
        deleted, _ = ClientFaceEncoding.objects.filter(client=client).delete()
        return deleted > 0
    
    def get_stats(self) -> dict:
        """
        Obtiene estadísticas de uso del reconocimiento facial.
        """
        from .models import ClientFaceEncoding, FaceRecognitionLog
        from django.db.models import Count, Avg
        from datetime import timedelta
        
        if not self.gym:
            return {}
        
        # Clientes registrados
        registered_count = ClientFaceEncoding.objects.filter(
            client__gym=self.gym
        ).count()
        
        # Total clientes activos
        total_clients = self.gym.clients.filter(status='active').count()
        
        # Logs de los últimos 30 días
        thirty_days_ago = timezone.now() - timedelta(days=30)
        recent_logs = FaceRecognitionLog.objects.filter(
            gym=self.gym,
            created_at__gte=thirty_days_ago
        )
        
        stats_by_result = recent_logs.values('result').annotate(
            count=Count('id')
        )
        
        avg_processing_time = recent_logs.filter(
            processing_time_ms__isnull=False
        ).aggregate(avg=Avg('processing_time_ms'))['avg']
        
        return {
            'registered_clients': registered_count,
            'total_active_clients': total_clients,
            'registration_rate': (registered_count / total_clients * 100) if total_clients > 0 else 0,
            'recent_attempts': {s['result']: s['count'] for s in stats_by_result},
            'avg_processing_time_ms': avg_processing_time or 0,
        }
