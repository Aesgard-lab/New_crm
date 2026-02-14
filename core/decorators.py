from functools import wraps
from django.http import JsonResponse
from django.core.exceptions import ValidationError, PermissionDenied
from django.http import Http404
import logging

logger = logging.getLogger(__name__)

def safe_api_view(view_func):
    """
    Decorator to standardize API error handling.
    Captures exceptions, logs them, and returns a safe JSON response.
    """
    @wraps(view_func)
    def _wrapped_view(request, *args, **kwargs):
        try:
            return view_func(request, *args, **kwargs)
        except ValidationError as e:
            # Django ValidationErrors can be dicts or lists
            if hasattr(e, 'message_dict'):
                errors = e.message_dict
            elif hasattr(e, 'messages'):
                errors = e.messages
            else:
                errors = str(e)
            return JsonResponse({'error': 'Validation Error', 'details': errors}, status=400)
        except PermissionDenied:
            return JsonResponse({'error': 'Permission Denied'}, status=403)
        except Http404:
            return JsonResponse({'error': 'Not Found'}, status=404)
        except Exception as e:
            # Log the full error with stack trace
            logger.exception(f"Internal API Error in {view_func.__name__}: {str(e)}")
            # Return generic error to user
            return JsonResponse({'error': 'Internal Server Error', 'message': 'An unexpected error occurred.'}, status=500)
            
    return _wrapped_view
