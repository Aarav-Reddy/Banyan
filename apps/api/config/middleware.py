import uuid

from django.http import JsonResponse


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
        return response
