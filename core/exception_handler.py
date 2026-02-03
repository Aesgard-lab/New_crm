"""
Manejador centralizado de excepciones para la API REST.

Proporciona:
- Respuestas de error consistentes
- Logging automático de errores
- Sanitización de información sensible
- Integración con Sentry

Uso en settings.py:
    REST_FRAMEWORK = {
        'EXCEPTION_HANDLER': 'core.exception_handler.custom_exception_handler',
    }
"""
import logging
import traceback
from typing import Optional

from django.conf import settings
from django.core.exceptions import (
    ObjectDoesNotExist,
    PermissionDenied,
    ValidationError as DjangoValidationError,
)
from django.db import IntegrityError
from django.http import Http404
from rest_framework import status
from rest_framework.exceptions import (
    APIException,
    AuthenticationFailed,
    NotAuthenticated,
    NotFound,
    ParseError,
    PermissionDenied as DRFPermissionDenied,
    Throttled,
    ValidationError as DRFValidationError,
)
from rest_framework.response import Response
from rest_framework.views import exception_handler as drf_exception_handler

logger = logging.getLogger('api.errors')


class APIError(APIException):
    """
    Excepción base para errores de API personalizados.
    
    Uso:
        raise APIError(
            message="El recurso no está disponible",
            code="RESOURCE_UNAVAILABLE",
            status_code=503,
        )
    """
    
    def __init__(
        self,
        message: str = "Error interno del servidor",
        code: str = "INTERNAL_ERROR",
        status_code: int = 500,
        details: dict = None,
    ):
        self.message = message
        self.code = code
        self.status_code = status_code
        self.details = details or {}
        super().__init__(detail=message)


class BusinessLogicError(APIError):
    """Error de lógica de negocio (reglas de dominio)."""
    
    def __init__(self, message: str, code: str = "BUSINESS_ERROR", details: dict = None):
        super().__init__(
            message=message,
            code=code,
            status_code=status.HTTP_400_BAD_REQUEST,
            details=details,
        )


class ResourceNotFoundError(APIError):
    """Recurso no encontrado."""
    
    def __init__(self, resource: str, identifier: str = None):
        message = f"{resource} no encontrado"
        if identifier:
            message = f"{resource} con id '{identifier}' no encontrado"
        super().__init__(
            message=message,
            code="NOT_FOUND",
            status_code=status.HTTP_404_NOT_FOUND,
        )


class ConflictError(APIError):
    """Conflicto de estado (ej: recurso ya existe)."""
    
    def __init__(self, message: str, details: dict = None):
        super().__init__(
            message=message,
            code="CONFLICT",
            status_code=status.HTTP_409_CONFLICT,
            details=details,
        )


class RateLimitError(APIError):
    """Error de rate limiting."""
    
    def __init__(self, retry_after: int = 60):
        super().__init__(
            message=f"Demasiadas solicitudes. Intenta de nuevo en {retry_after} segundos.",
            code="RATE_LIMIT_EXCEEDED",
            status_code=status.HTTP_429_TOO_MANY_REQUESTS,
            details={"retry_after": retry_after},
        )


def format_error_response(
    message: str,
    code: str,
    status_code: int,
    details: dict = None,
    field_errors: dict = None,
) -> dict:
    """
    Formatea una respuesta de error de manera consistente.
    
    Estructura:
    {
        "error": {
            "message": "Descripción del error",
            "code": "ERROR_CODE",
            "details": {...},
            "field_errors": {...}
        }
    }
    """
    error_data = {
        "message": message,
        "code": code,
    }
    
    if details:
        error_data["details"] = details
    
    if field_errors:
        error_data["field_errors"] = field_errors
    
    return {"error": error_data}


def extract_field_errors(detail) -> dict:
    """Extrae errores de campo de la estructura de DRF."""
    if isinstance(detail, dict):
        return {
            field: errors if isinstance(errors, list) else [str(errors)]
            for field, errors in detail.items()
        }
    return {}


def custom_exception_handler(exc, context) -> Optional[Response]:
    """
    Manejador personalizado de excepciones para la API.
    
    Convierte todas las excepciones a un formato consistente
    y registra errores para debugging.
    """
    # Primero, dejar que DRF maneje lo que pueda
    response = drf_exception_handler(exc, context)
    
    # Obtener información del request para logging
    request = context.get('request')
    view = context.get('view')
    
    log_context = {
        'view': view.__class__.__name__ if view else 'Unknown',
        'method': request.method if request else 'Unknown',
        'path': request.path if request else 'Unknown',
        'user_id': str(request.user.pk) if request and request.user.is_authenticated else None,
    }
    
    # Si DRF ya manejó la excepción, formatear la respuesta
    if response is not None:
        return _handle_drf_exception(exc, response, log_context)
    
    # Manejar excepciones que DRF no captura
    return _handle_unhandled_exception(exc, log_context)


def _handle_drf_exception(exc, response: Response, log_context: dict) -> Response:
    """Maneja excepciones capturadas por DRF."""
    
    # Determinar código y mensaje según tipo de excepción
    if isinstance(exc, DRFValidationError):
        code = "VALIDATION_ERROR"
        message = "Error de validación"
        field_errors = extract_field_errors(exc.detail)
        
        logger.warning(
            f"Validation error: {exc.detail}",
            extra=log_context,
        )
        
        response.data = format_error_response(
            message=message,
            code=code,
            status_code=response.status_code,
            field_errors=field_errors,
        )
    
    elif isinstance(exc, (NotAuthenticated, AuthenticationFailed)):
        code = "AUTHENTICATION_ERROR"
        message = "Autenticación requerida" if isinstance(exc, NotAuthenticated) else "Credenciales inválidas"
        
        logger.info(f"Auth failed: {type(exc).__name__}", extra=log_context)
        
        response.data = format_error_response(
            message=message,
            code=code,
            status_code=response.status_code,
        )
    
    elif isinstance(exc, (DRFPermissionDenied, PermissionDenied)):
        code = "PERMISSION_DENIED"
        message = "No tienes permisos para realizar esta acción"
        
        logger.warning(f"Permission denied", extra=log_context)
        
        response.data = format_error_response(
            message=message,
            code=code,
            status_code=response.status_code,
        )
    
    elif isinstance(exc, NotFound):
        code = "NOT_FOUND"
        message = "Recurso no encontrado"
        
        response.data = format_error_response(
            message=message,
            code=code,
            status_code=response.status_code,
        )
    
    elif isinstance(exc, Throttled):
        code = "RATE_LIMIT_EXCEEDED"
        message = f"Demasiadas solicitudes. Intenta de nuevo en {exc.wait or 60} segundos."
        
        logger.warning(f"Rate limit hit", extra=log_context)
        
        response.data = format_error_response(
            message=message,
            code=code,
            status_code=response.status_code,
            details={"retry_after": exc.wait or 60},
        )
    
    elif isinstance(exc, ParseError):
        code = "PARSE_ERROR"
        message = "Error al procesar la solicitud"
        
        response.data = format_error_response(
            message=message,
            code=code,
            status_code=response.status_code,
        )
    
    elif isinstance(exc, APIError):
        response.data = format_error_response(
            message=exc.message,
            code=exc.code,
            status_code=exc.status_code,
            details=exc.details,
        )
    
    else:
        # Otras excepciones de API
        message = str(exc.detail) if hasattr(exc, 'detail') else str(exc)
        code = getattr(exc, 'default_code', 'ERROR')
        
        response.data = format_error_response(
            message=message,
            code=code.upper(),
            status_code=response.status_code,
        )
    
    return response


def _handle_unhandled_exception(exc, log_context: dict) -> Response:
    """Maneja excepciones no capturadas por DRF."""
    
    # Django 404
    if isinstance(exc, Http404):
        return Response(
            format_error_response(
                message="Recurso no encontrado",
                code="NOT_FOUND",
                status_code=404,
            ),
            status=status.HTTP_404_NOT_FOUND,
        )
    
    # Django ObjectDoesNotExist
    if isinstance(exc, ObjectDoesNotExist):
        return Response(
            format_error_response(
                message="Recurso no encontrado",
                code="NOT_FOUND",
                status_code=404,
            ),
            status=status.HTTP_404_NOT_FOUND,
        )
    
    # Django ValidationError
    if isinstance(exc, DjangoValidationError):
        field_errors = {}
        if hasattr(exc, 'message_dict'):
            field_errors = exc.message_dict
        elif hasattr(exc, 'messages'):
            field_errors = {'__all__': exc.messages}
        
        return Response(
            format_error_response(
                message="Error de validación",
                code="VALIDATION_ERROR",
                status_code=400,
                field_errors=field_errors,
            ),
            status=status.HTTP_400_BAD_REQUEST,
        )
    
    # IntegrityError (ej: unique constraint)
    if isinstance(exc, IntegrityError):
        logger.error(
            f"Database integrity error: {exc}",
            extra=log_context,
            exc_info=True,
        )
        return Response(
            format_error_response(
                message="Error de integridad de datos. El recurso puede ya existir.",
                code="INTEGRITY_ERROR",
                status_code=409,
            ),
            status=status.HTTP_409_CONFLICT,
        )
    
    # Error no manejado - loggearlo y devolver error genérico
    logger.error(
        f"Unhandled exception: {type(exc).__name__}: {exc}",
        extra={**log_context, 'traceback': traceback.format_exc()},
        exc_info=True,
    )
    
    # En producción, no revelar detalles del error
    if settings.DEBUG:
        message = f"{type(exc).__name__}: {exc}"
        details = {"traceback": traceback.format_exc().split('\n')}
    else:
        message = "Error interno del servidor"
        details = None
    
    return Response(
        format_error_response(
            message=message,
            code="INTERNAL_ERROR",
            status_code=500,
            details=details,
        ),
        status=status.HTTP_500_INTERNAL_SERVER_ERROR,
    )
