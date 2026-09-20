import logging
import uuid

from django.conf import settings
from django.http import JsonResponse
from django.utils.deprecation import MiddlewareMixin


class DemoReadOnlyMiddleware(MiddlewareMixin):
    """Deny visitor mutations before dispatch; sessions retain their CSRF checks."""

    def process_view(self, request, view_func, view_args, view_kwargs):
        if not (settings.DEMO_MODE and settings.DEMO_READ_ONLY):
            return None
        if request.method in {"GET", "HEAD", "OPTIONS"}:
            return None

        from philanthra.accounts.views import LoginView, LogoutView

        if request.method == "POST" and getattr(view_func, "view_class", None) in {
            LoginView,
            LogoutView,
        }:
            return None
        return JsonResponse(
            {
                "error": {
                    "code": "demo_read_only",
                    "message": "This public demo is read-only. Changes are disabled.",
                    "fields": {},
                }
            },
            status=403,
        )


def csrf_failure(request, reason=""):
    return JsonResponse(
        {
            "error": {
                "code": "csrf_failed",
                "message": "Refresh the session and retry.",
                "fields": {},
            }
        },
        status=403,
    )


class RequestMetadataMiddleware:
    def __init__(self, get_response):
        self.get_response = get_response

    def __call__(self, request):
        request.correlation_id = str(uuid.uuid4())
        response = self.get_response(request)
        response["X-Request-ID"] = request.correlation_id
        response["Cache-Control"] = "private, no-store"
        response["X-Content-Type-Options"] = "nosniff"
        response["X-Frame-Options"] = "DENY"
        logging.getLogger("philanthra.requests").info(
            "request_completed",
            extra={
                "request_id": request.correlation_id,
                "status": response.status_code,
                "method": request.method,
            },
        )
        return response
