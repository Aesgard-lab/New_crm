"""
Utilidades centralizadas para respuestas de API.

Proporciona funciones helper para generar respuestas JSON
consistentes en toda la aplicación.

Uso:
    from core.api_utils import api_success, api_error

    def my_view(request):
        if error:
            return api_error("Algo salió mal", code="VALIDATION_ERROR")
        return api_success({"user": user_data}, message="Usuario creado")
"""
from typing import Any, Optional
from django.http import JsonResponse


def api_success(
    data: Optional[dict] = None,
    message: Optional[str] = None,
    status: int = 200,
) -> JsonResponse:
    """
    Genera una respuesta JSON de éxito.

    Args:
        data: Datos a incluir en la respuesta
        message: Mensaje opcional de éxito
        status: Código de estado HTTP (default 200)

    Returns:
        JsonResponse con formato consistente

    Example:
        return api_success({"user_id": 123}, message="Usuario creado")
        # {"success": true, "message": "Usuario creado", "user_id": 123}
    """
    response = {"success": True}

    if message:
        response["message"] = message

    if data:
        response.update(data)

    return JsonResponse(response, status=status)


def api_error(
    message: str,
    code: Optional[str] = None,
    status: int = 400,
    details: Optional[dict] = None,
    field_errors: Optional[dict] = None,
) -> JsonResponse:
    """
    Genera una respuesta JSON de error.

    Args:
        message: Mensaje de error para el usuario
        code: Código de error para programas (ej: "VALIDATION_ERROR")
        status: Código de estado HTTP (default 400)
        details: Detalles adicionales del error
        field_errors: Errores por campo para formularios

    Returns:
        JsonResponse con formato consistente

    Example:
        return api_error("Email inválido", code="INVALID_EMAIL", status=400)
        # {"success": false, "error": "Email inválido", "code": "INVALID_EMAIL"}
    """
    response = {
        "success": False,
        "error": message,
    }

    if code:
        response["code"] = code

    if details:
        response["details"] = details

    if field_errors:
        response["field_errors"] = field_errors

    return JsonResponse(response, status=status)


def api_paginated(
    items: list,
    page: int,
    page_size: int,
    total: int,
    extra: Optional[dict] = None,
) -> JsonResponse:
    """
    Genera una respuesta JSON paginada.

    Args:
        items: Lista de elementos de la página actual
        page: Número de página actual (1-indexed)
        page_size: Tamaño de página
        total: Total de elementos
        extra: Datos adicionales a incluir

    Returns:
        JsonResponse con formato de paginación consistente
    """
    total_pages = (total + page_size - 1) // page_size if page_size > 0 else 0

    response = {
        "success": True,
        "data": items,
        "pagination": {
            "page": page,
            "page_size": page_size,
            "total": total,
            "total_pages": total_pages,
            "has_next": page < total_pages,
            "has_prev": page > 1,
        },
    }

    if extra:
        response.update(extra)

    return JsonResponse(response)


def api_created(
    data: Optional[dict] = None,
    message: str = "Recurso creado correctamente",
) -> JsonResponse:
    """Shortcut para respuesta de creación (201)."""
    return api_success(data, message=message, status=201)


def api_deleted(message: str = "Recurso eliminado correctamente") -> JsonResponse:
    """Shortcut para respuesta de eliminación."""
    return api_success(message=message)


def api_not_found(resource: str = "Recurso") -> JsonResponse:
    """Shortcut para error 404."""
    return api_error(f"{resource} no encontrado", code="NOT_FOUND", status=404)


def api_unauthorized(message: str = "No autorizado") -> JsonResponse:
    """Shortcut para error 401."""
    return api_error(message, code="UNAUTHORIZED", status=401)


def api_forbidden(message: str = "Acceso denegado") -> JsonResponse:
    """Shortcut para error 403."""
    return api_error(message, code="FORBIDDEN", status=403)


def api_validation_error(
    message: str = "Error de validación",
    field_errors: Optional[dict] = None,
) -> JsonResponse:
    """Shortcut para errores de validación."""
    return api_error(
        message,
        code="VALIDATION_ERROR",
        status=400,
        field_errors=field_errors,
    )
