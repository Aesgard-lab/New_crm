from django.contrib import admin
from django.urls import path, include

urlpatterns = [
    # Admin Django
    path("admin/", admin.site.urls),

    # Backoffice (panel interno del gym)
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
]

from django.conf import settings
from django.conf.urls.static import static

if settings.DEBUG:
    urlpatterns += static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)
