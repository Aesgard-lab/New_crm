"""
Vistas para Health Checks.

Endpoints:
- /health/live/   - Liveness probe (siempre 200 si Django corre)
- /health/ready/  - Readiness probe (200 si puede recibir trafico)
- /health/        - Estado detallado de todos los componentes
"""

from django.http import JsonResponse
from django.views import View
from django.views.decorators.csrf import csrf_exempt
from django.utils.decorators import method_decorator

from core.health import health_checker, HealthStatus


@method_decorator(csrf_exempt, name='dispatch')
class LivenessView(View):
    """
    Liveness probe - indica si la aplicacion esta corriendo.
    
    Uso: Docker HEALTHCHECK, Kubernetes livenessProbe
    
    Respuestas:
    - 200: Aplicacion corriendo
    - 503: Aplicacion no responde (implicitamente si no responde)
    """
    
    def get(self, request):
        if health_checker.is_live():
            return JsonResponse({
                "status": "alive",
                "message": "Application is running",
            }, status=200)
        else:
            return JsonResponse({
                "status": "dead",
                "message": "Application is not responding",
            }, status=503)


@method_decorator(csrf_exempt, name='dispatch')
class ReadinessView(View):
    """
    Readiness probe - indica si la aplicacion puede recibir trafico.
    
    Uso: Kubernetes readinessProbe, load balancer health checks
    
    Respuestas:
    - 200: Lista para recibir trafico
    - 503: No lista (DB no disponible, etc.)
    """
    
    def get(self, request):
        if health_checker.is_ready():
            return JsonResponse({
                "status": "ready",
                "message": "Application is ready to receive traffic",
            }, status=200)
        else:
            return JsonResponse({
                "status": "not_ready",
                "message": "Application is not ready to receive traffic",
            }, status=503)


@method_decorator(csrf_exempt, name='dispatch')
class HealthView(View):
    """
    Health check detallado - estado de todos los componentes.
    
    Uso: Dashboards de monitoreo, debugging
    
    Respuestas:
    - 200: Sistema saludable o degradado
    - 503: Sistema no saludable (componente critico caido)
    
    Parametros:
    - ?verbose=true: Incluir detalles adicionales
    """
    
    def get(self, request):
        verbose = request.GET.get('verbose', '').lower() == 'true'
        
        report = health_checker.get_health_report()
        response_data = report.to_dict()
        
        # Si no es verbose, simplificar la respuesta
        if not verbose:
            response_data = {
                "status": report.status.value,
                "version": report.version,
                "environment": report.environment,
                "components": {
                    c.name: c.status.value 
                    for c in report.components
                },
            }
        
        # Determinar status code
        if report.status == HealthStatus.UNHEALTHY:
            status_code = 503
        else:
            status_code = 200
        
        return JsonResponse(response_data, status=status_code)


@method_decorator(csrf_exempt, name='dispatch')
class PingView(View):
    """
    Ping simple - respuesta minima para checks muy frecuentes.
    
    Uso: Load balancers, monitoring cada segundo
    """
    
    def get(self, request):
        return JsonResponse({"pong": True}, status=200)
