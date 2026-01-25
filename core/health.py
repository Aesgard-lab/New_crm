"""
Sistema de Health Checks para monitoreo de la aplicacion.

Proporciona endpoints para:
- Liveness: La aplicacion esta corriendo
- Readiness: La aplicacion puede recibir trafico
- Health: Estado detallado de todos los componentes

Uso con Docker:
    healthcheck:
      test: ["CMD", "curl", "-f", "http://localhost:8000/health/live/"]
      interval: 30s
      timeout: 10s
      retries: 3

Uso con Kubernetes:
    livenessProbe:
      httpGet:
        path: /health/live/
        port: 8000
    readinessProbe:
      httpGet:
        path: /health/ready/
        port: 8000
"""

import time
import socket
import logging
from dataclasses import dataclass, field
from typing import Optional
from enum import Enum

from django.conf import settings
from django.core.cache import cache
from django.db import connection

logger = logging.getLogger(__name__)


class HealthStatus(Enum):
    """Estados posibles de salud."""
    HEALTHY = "healthy"
    DEGRADED = "degraded"
    UNHEALTHY = "unhealthy"


@dataclass
class ComponentHealth:
    """Estado de salud de un componente."""
    name: str
    status: HealthStatus
    latency_ms: Optional[float] = None
    message: Optional[str] = None
    details: dict = field(default_factory=dict)
    
    def to_dict(self) -> dict:
        result = {
            "name": self.name,
            "status": self.status.value,
        }
        if self.latency_ms is not None:
            result["latency_ms"] = round(self.latency_ms, 2)
        if self.message:
            result["message"] = self.message
        if self.details:
            result["details"] = self.details
        return result


@dataclass
class HealthReport:
    """Reporte completo de salud del sistema."""
    status: HealthStatus
    components: list
    version: str
    environment: str
    timestamp: str
    
    def to_dict(self) -> dict:
        return {
            "status": self.status.value,
            "version": self.version,
            "environment": self.environment,
            "timestamp": self.timestamp,
            "components": [c.to_dict() for c in self.components],
        }


class HealthChecker:
    """
    Verificador de salud del sistema.
    
    Comprueba el estado de:
    - Base de datos PostgreSQL
    - Cache Redis
    - Celery workers
    - Sistema de archivos
    - Servicios externos (opcional)
    """
    
    def __init__(self):
        self.checks = [
            ("database", self.check_database),
            ("cache", self.check_cache),
            ("filesystem", self.check_filesystem),
        ]
        
        # Agregar check de Celery si esta configurado
        if hasattr(settings, 'CELERY_BROKER_URL'):
            self.checks.append(("celery", self.check_celery))
    
    def check_database(self) -> ComponentHealth:
        """Verificar conexion a la base de datos."""
        start = time.time()
        try:
            with connection.cursor() as cursor:
                cursor.execute("SELECT 1")
                cursor.fetchone()
            
            latency = (time.time() - start) * 1000
            
            # Degradado si latencia > 100ms
            status = HealthStatus.HEALTHY if latency < 100 else HealthStatus.DEGRADED
            
            return ComponentHealth(
                name="database",
                status=status,
                latency_ms=latency,
                details={
                    "engine": settings.DATABASES['default']['ENGINE'],
                    "name": settings.DATABASES['default'].get('NAME', 'unknown'),
                }
            )
        except Exception as e:
            logger.error(f"Database health check failed: {e}")
            return ComponentHealth(
                name="database",
                status=HealthStatus.UNHEALTHY,
                message=str(e),
            )
    
    def check_cache(self) -> ComponentHealth:
        """Verificar conexion al cache (Redis)."""
        start = time.time()
        test_key = "_health_check_test"
        test_value = "ok"
        
        try:
            # Escribir y leer del cache
            cache.set(test_key, test_value, timeout=10)
            result = cache.get(test_key)
            cache.delete(test_key)
            
            latency = (time.time() - start) * 1000
            
            if result != test_value:
                return ComponentHealth(
                    name="cache",
                    status=HealthStatus.DEGRADED,
                    latency_ms=latency,
                    message="Cache read/write mismatch",
                )
            
            status = HealthStatus.HEALTHY if latency < 50 else HealthStatus.DEGRADED
            
            return ComponentHealth(
                name="cache",
                status=status,
                latency_ms=latency,
                details={
                    "backend": settings.CACHES.get('default', {}).get('BACKEND', 'unknown'),
                }
            )
        except Exception as e:
            logger.warning(f"Cache health check failed: {e}")
            # Cache no disponible es degradado, no critico
            return ComponentHealth(
                name="cache",
                status=HealthStatus.DEGRADED,
                message=str(e),
            )
    
    def check_filesystem(self) -> ComponentHealth:
        """Verificar acceso al sistema de archivos."""
        start = time.time()
        
        try:
            media_root = settings.MEDIA_ROOT
            static_root = settings.STATIC_ROOT
            
            # Verificar que los directorios existen o se pueden crear
            from pathlib import Path
            
            media_path = Path(media_root)
            media_ok = media_path.exists() or media_path.parent.exists()
            
            static_path = Path(static_root)
            static_ok = static_path.exists() or static_path.parent.exists()
            
            latency = (time.time() - start) * 1000
            
            if media_ok and static_ok:
                return ComponentHealth(
                    name="filesystem",
                    status=HealthStatus.HEALTHY,
                    latency_ms=latency,
                    details={
                        "media_root": str(media_root),
                        "static_root": str(static_root),
                    }
                )
            else:
                return ComponentHealth(
                    name="filesystem",
                    status=HealthStatus.DEGRADED,
                    latency_ms=latency,
                    message="Some directories not accessible",
                    details={
                        "media_ok": media_ok,
                        "static_ok": static_ok,
                    }
                )
        except Exception as e:
            logger.error(f"Filesystem health check failed: {e}")
            return ComponentHealth(
                name="filesystem",
                status=HealthStatus.UNHEALTHY,
                message=str(e),
            )
    
    def check_celery(self) -> ComponentHealth:
        """Verificar conexion a Celery broker."""
        start = time.time()
        
        try:
            from celery import current_app
            
            # Intentar conectar al broker
            conn = current_app.connection()
            conn.ensure_connection(max_retries=1, timeout=5)
            conn.close()
            
            latency = (time.time() - start) * 1000
            
            return ComponentHealth(
                name="celery",
                status=HealthStatus.HEALTHY,
                latency_ms=latency,
                details={
                    "broker": settings.CELERY_BROKER_URL.split('@')[-1] if '@' in settings.CELERY_BROKER_URL else settings.CELERY_BROKER_URL,
                }
            )
        except Exception as e:
            logger.warning(f"Celery health check failed: {e}")
            return ComponentHealth(
                name="celery",
                status=HealthStatus.DEGRADED,
                message=str(e),
            )
    
    def is_live(self) -> bool:
        """
        Liveness check - la aplicacion esta corriendo.
        Solo verifica que Python/Django estan funcionando.
        """
        return True
    
    def is_ready(self) -> bool:
        """
        Readiness check - la aplicacion puede recibir trafico.
        Verifica que los componentes criticos estan disponibles.
        """
        try:
            # Solo verificar DB que es critica
            db_health = self.check_database()
            return db_health.status != HealthStatus.UNHEALTHY
        except Exception:
            return False
    
    def get_health_report(self) -> HealthReport:
        """
        Obtener reporte completo de salud.
        Ejecuta todos los checks y genera un reporte.
        """
        from datetime import datetime
        
        components = []
        overall_status = HealthStatus.HEALTHY
        
        for name, check_func in self.checks:
            try:
                health = check_func()
                components.append(health)
                
                # Actualizar estado general
                if health.status == HealthStatus.UNHEALTHY:
                    overall_status = HealthStatus.UNHEALTHY
                elif health.status == HealthStatus.DEGRADED and overall_status == HealthStatus.HEALTHY:
                    overall_status = HealthStatus.DEGRADED
                    
            except Exception as e:
                logger.error(f"Health check '{name}' failed with exception: {e}")
                components.append(ComponentHealth(
                    name=name,
                    status=HealthStatus.UNHEALTHY,
                    message=f"Check failed: {e}",
                ))
                overall_status = HealthStatus.UNHEALTHY
        
        return HealthReport(
            status=overall_status,
            components=components,
            version=getattr(settings, 'APP_VERSION', '1.0.0'),
            environment=getattr(settings, 'ENVIRONMENT', 'unknown'),
            timestamp=datetime.utcnow().isoformat() + 'Z',
        )


# Instancia global del checker
health_checker = HealthChecker()
