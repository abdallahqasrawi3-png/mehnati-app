import logging

from django.core.exceptions import ValidationError as DjangoValidationError
from rest_framework import status
from rest_framework.exceptions import ValidationError
from rest_framework.response import Response
from rest_framework.views import exception_handler

logger = logging.getLogger(__name__)


class BusinessRuleError(Exception):
    """Raised by service functions when a business rule blocks an action."""

    def __init__(self, message, code="rule_violation"):
        super().__init__(message)
        self.message = message
        self.code = code


def api_exception_handler(exc, context):
    if isinstance(exc, BusinessRuleError):
        return Response({"detail": exc.message, "code": exc.code}, status=status.HTTP_400_BAD_REQUEST)
    if isinstance(exc, DjangoValidationError):
        exc = ValidationError(exc.message_dict if hasattr(exc, "message_dict") else exc.messages)
    response = exception_handler(exc, context)
    if response is None:
        # Unexpected error: log details server-side, return a generic message.
        logger.exception("Unhandled API error")
        return Response(
            {"detail": "حدث خطأ غير متوقع. حاول مرة أخرى لاحقًا."},
            status=status.HTTP_500_INTERNAL_SERVER_ERROR,
        )
    return response
