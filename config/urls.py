from django.contrib import admin
from django.urls import path, include
from django.views.generic import TemplateView
from django.http import JsonResponse
# URLs config
from django.conf import settings
from django.conf.urls.static import static
from drf_spectacular.views import SpectacularAPIView, SpectacularRedocView, SpectacularSwaggerView

# Calendar feed view (público, sin autenticación)
from clients.calendar_views import calendar_feed


urlpatterns = [
    # Health Check endpoints (para Docker, Kubernetes, Load Balancers)
    path("health/", include("core.urls", namespace="health")),
    
    # Calendar Feed (público, para suscripción desde apps de calendario)
    path("calendar/feed/<str:token>.ics", calendar_feed, name="calendar_feed"),
    
    # API Documentation (OpenAPI / Swagger)
    path("api/schema/", SpectacularAPIView.as_view(), name="schema"),
    path("api/docs/", SpectacularSwaggerView.as_view(url_name="schema"), name="swagger-ui"),
    path("api/redoc/", SpectacularRedocView.as_view(url_name="schema"), name="redoc"),
    
    # Admin Django
    path("admin/", admin.site.urls),

    # PWA Offline page
    path("offline/", TemplateView.as_view(template_name="offline.html"), name="offline"),

    # SaaS Billing (Webhooks, etc)
    path("billing/", include("saas_billing.urls")),

    # Public Portal y Widgets Embebibles - DEBE IR ANTES DEL BACKOFFICE
    path("public/", include("public_portal.urls")),
    path("embed/", include(("public_portal.embed_urls", "embed"), namespace="embed")),
    
    # Superadmin Panel
    path("superadmin/", include(("superadmin.urls", "superadmin"), namespace="superadmin")),

    # Backoffice (panel interno del gym)
    path("", include("backoffice.urls")),
    path("staff/", include("staff.urls")),
    path("activities/", include("activities.urls")),
    path("services/", include("services.urls")),
    path("products/", include("products.urls")),
    path("memberships/", include("memberships.urls")),
    path("sales/", include("sales.urls")),
    path("finance/", include("finance.urls")),
    path("marketing/", include("marketing.urls")),
    path("reporting/", include("reporting.urls")),
    path("routines/", include("routines.urls")),
    path("gamification/", include(("gamification.urls", "gamification"), namespace="gamification")),
    path("providers/", include(("providers.urls", "providers"), namespace="providers")),
    path("access/", include(("access_control.urls", "access_control"), namespace="access_control")),
    path("lockers/", include(("lockers.urls", "lockers"), namespace="lockers")),
    path("face-recognition/", include(("facial_checkin.urls", "facial_checkin"), namespace="facial_checkin")),

    # Member Portal (App Socios)
    path("portal/", include("clients.urls")),

    # Organizations / Franchise
    path("organizations/", include("organizations.urls")),

    # Mobile API
    path("api/", include("api.urls")),
]

if settings.DEBUG:
    urlpatterns += static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)
    urlpatterns += static(settings.STATIC_URL, document_root=settings.STATICFILES_DIRS[0] if settings.STATICFILES_DIRS else settings.STATIC_ROOT)
