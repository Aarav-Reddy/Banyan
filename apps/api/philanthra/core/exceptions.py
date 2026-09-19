from django.core.exceptions import ValidationError as DjangoValidationError
from django.http import Http404
from rest_framework.exceptions import ValidationError
from rest_framework.views import exception_handler as drf_exception_handler


def exception_handler(exc, context):
    if isinstance(exc, DjangoValidationError):
        exc = ValidationError(exc.message_dict if hasattr(exc, "message_dict") else exc.messages)
    response = drf_exception_handler(exc, context)
    if response is None:
        return None
    code = getattr(
        exc, "default_code", "not_found" if isinstance(exc, Http404) else "request_failed"
    )
    data = response.data
    message = (
        str(data.get("detail"))
        if isinstance(data, dict) and "detail" in data
        else "Please correct the highlighted fields."
    )
    fields = data if isinstance(data, dict) and "detail" not in data else {}
    response.data = {"error": {"code": code, "message": message, "fields": fields}}
    return response
