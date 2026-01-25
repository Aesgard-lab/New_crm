"""
URLs para Health Checks.

Endpoints:
- /health/         - Estado detallado del sistema
- /health/live/    - Liveness probe
- /health/ready/   - Readiness probe
- /health/ping/    - Ping simple
"""

from django.urls import path
from core.health_views import (
    HealthView,
    LivenessView,
    ReadinessView,
    PingView,
)

app_name = 'health'

urlpatterns = [
    path('', HealthView.as_view(), name='health'),
    path('live/', LivenessView.as_view(), name='liveness'),
    path('ready/', ReadinessView.as_view(), name='readiness'),
    path('ping/', PingView.as_view(), name='ping'),
]
