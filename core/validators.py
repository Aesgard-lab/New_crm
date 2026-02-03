"""
Validadores personalizados para archivos subidos.

SECURITY: Estos validadores previenen uploads maliciosos.
"""
import os
from django.core.exceptions import ValidationError


# Extensiones permitidas para imágenes
ALLOWED_IMAGE_EXTENSIONS = ['.jpg', '.jpeg', '.png', '.gif', '.webp']  # SVG removido por riesgo XSS

# Extensiones permitidas para documentos
ALLOWED_DOCUMENT_EXTENSIONS = ['.pdf', '.doc', '.docx', '.xls', '.xlsx', '.txt', '.csv']

# Tamaño máximo de archivo (10MB)
MAX_FILE_SIZE = 10 * 1024 * 1024  # 10MB en bytes

# SECURITY: Magic bytes para validar tipo real del archivo
IMAGE_MAGIC_BYTES = {
    b'\xff\xd8\xff': 'jpeg',  # JPEG
    b'\x89PNG': 'png',        # PNG
    b'GIF87a': 'gif',         # GIF87a
    b'GIF89a': 'gif',         # GIF89a
    b'RIFF': 'webp',          # WebP (requiere verificación adicional)
}


def _check_image_magic_bytes(file):
    """
    SECURITY: Verifica que el contenido del archivo coincida con su extensión.
    Previene ataques donde archivos maliciosos se renombran con extensiones de imagen.
    """
    # Leer primeros bytes
    file.seek(0)
    header = file.read(12)
    file.seek(0)  # Reset para uso posterior
    
    # Verificar contra magic bytes conocidos
    is_valid_image = False
    for magic, img_type in IMAGE_MAGIC_BYTES.items():
        if header.startswith(magic):
            is_valid_image = True
            break
    
    # Verificación especial para WebP (RIFF....WEBP)
    if header[:4] == b'RIFF' and header[8:12] == b'WEBP':
        is_valid_image = True
    
    return is_valid_image


def validate_image_file(file):
    """
    Valida que el archivo sea una imagen permitida.
    
    SECURITY: Verifica tanto extensión como magic bytes.
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
    
    # SECURITY: Verificar magic bytes
    if hasattr(file, 'read'):
        if not _check_image_magic_bytes(file):
            raise ValidationError(
                'El archivo no parece ser una imagen válida. '
                'Asegúrese de subir un archivo de imagen real.'
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
