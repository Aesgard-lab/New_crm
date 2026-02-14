from rest_framework.views import APIView
from rest_framework.response import Response
from django.core.exceptions import ValidationError as DjangoValidationError
from django.http import Http404
from rest_framework.exceptions import APIException
import logging

logger = logging.getLogger(__name__)

class SafeAPIView(APIView):
    """
    Base APIView that catches all exceptions and returns standard JSON errors.
    Replaces repetitive try/except blocks in views.
    """
    def handle_exception(self, exc):
        if isinstance(exc, DjangoValidationError):
            # Handle Django validation errors (convert to DRF format or dict)
            if hasattr(exc, 'message_dict'):
                data = exc.message_dict
            elif hasattr(exc, 'messages'):
                data = exc.messages
            else:
                data = str(exc)
            return Response({'error': 'Validation Error', 'details': data}, status=400)

        # Call DRF's default handler first
        response = super().handle_exception(exc)
        
        if response is not None:
            return response

        # If response is None, it's an unhandled exception (500)
        logger.exception(f"Unexpected API Error: {str(exc)}")
        return Response({
            'error': 'Internal Server Error',
            'message': 'An unexpected error occurred.'
        }, status=500)
