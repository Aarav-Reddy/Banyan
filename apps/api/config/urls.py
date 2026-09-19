from django.db import connection
from django.http import JsonResponse
from django.urls import include, path
from drf_spectacular.views import SpectacularAPIView
from philanthra.explanations.views import ExplanationView


def health(request):
    return JsonResponse({"data": {"status": "ok", "service": "philanthra-api"}})


def ready(request):
    try:
        with connection.cursor() as cursor:
            cursor.execute("SELECT 1")
        return JsonResponse({"data": {"status": "ready"}})
    except Exception:
        return JsonResponse(
            {
                "error": {
                    "code": "database_unavailable",
                    "message": "Database not ready",
                    "fields": {},
                }
            },
            status=503,
        )


urlpatterns = [
    path("api/health/", health),
    path("api/ready/", ready),
    path("api/v1/schema/", SpectacularAPIView.as_view(), name="schema"),
    path("api/v1/explanations/<uuid:pk>/", ExplanationView.as_view()),
    path("api/v1/pilot/", include("philanthra.pilot.urls")),
    path("api/v1/", include("philanthra.core.urls")),
]
