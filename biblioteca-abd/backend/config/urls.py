from django.contrib import admin
from django.urls import include, path
from drf_spectacular.views import (
    SpectacularAPIView,
    SpectacularRedocView,
    SpectacularSwaggerView,
)
from rest_framework.response import Response
from rest_framework.views import APIView


class HealthView(APIView):
    authentication_classes: list = []
    permission_classes: list = []

    def get(self, request, *args, **kwargs):
        return Response({"status": "ok"})


urlpatterns = [
    path("admin/", admin.site.urls),
    path("health", HealthView.as_view(), name="health"),
    path("api/schema/", SpectacularAPIView.as_view(), name="schema"),
    path("api/schema/swagger/", SpectacularSwaggerView.as_view(url_name="schema")),
    path("api/schema/redoc/", SpectacularRedocView.as_view(url_name="schema")),
    path("api/auth/", include("apps.authx.urls")),
    path("api/", include("apps.catalog.urls")),
    path("api/", include("apps.reviews.urls")),
    path("api/", include("apps.reco.urls")),
    path("api/", include("apps.ingestion.urls")),
]
