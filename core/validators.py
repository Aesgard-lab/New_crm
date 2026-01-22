"""
Validadores personalizados para archivos subidos
"""
import os
from django.core.exceptions import ValidationError


# Extensiones permitidas para imágenes
ALLOWED_IMAGE_EXTENSIONS = ['.jpg', '.jpeg', '.png', '.gif', '.webp', '.svg']

# Extensiones permitidas para documentos
ALLOWED_DOCUMENT_EXTENSIONS = ['.pdf', '.doc', '.docx', '.xls', '.xlsx', '.txt', '.csv']

# Tamaño máximo de archivo (10MB)
MAX_FILE_SIZE = 10 * 1024 * 1024  # 10MB en bytes


def validate_image_file(file):
    """
    Valida que el archivo sea una imagen permitida
    """
    ext = os.path.splitext(file.name)[1].lower()
    if ext not in ALLOWED_IMAGE_EXTENSIONS:
        raise ValidationError(
            f'Tipo de archivo no permitido. Solo se aceptan: {", ".join(ALLOWED_IMAGE_EXTENSIONS)}'
        )
    
    if file.size > MAX_FILE_SIZE:
        raise ValidationError(
            f'El archivo es demasiado grande. Tamaño máximo: {MAX_FILE_SIZE // (1024*1024)}MB'
        )
    
    return file


def validate_document_file(file):
    """
    Valida que el archivo sea un documento permitido
    """
    ext = os.path.splitext(file.name)[1].lower()
    if ext not in ALLOWED_DOCUMENT_EXTENSIONS:
        raise ValidationError(
            f'Tipo de archivo no permitido. Solo se aceptan: {", ".join(ALLOWED_DOCUMENT_EXTENSIONS)}'
        )
    
    if file.size > MAX_FILE_SIZE:
        raise ValidationError(
            f'El archivo es demasiado grande. Tamaño máximo: {MAX_FILE_SIZE // (1024*1024)}MB'
        )
    
    return file


def validate_any_file(file):
    """
    Validación general de archivos (solo tamaño)
    """
    if file.size > MAX_FILE_SIZE:
        raise ValidationError(
            f'El archivo es demasiado grande. Tamaño máximo: {MAX_FILE_SIZE // (1024*1024)}MB'
        )
    
    return file
