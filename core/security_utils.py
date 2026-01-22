"""
Utilidades de seguridad para cifrado de datos sensibles
"""
from cryptography.fernet import Fernet
from django.conf import settings
import base64
import hashlib


def get_encryption_key():
    """
    Genera una clave de cifrado derivada de SECRET_KEY
    """
    key = hashlib.sha256(settings.SECRET_KEY.encode()).digest()
    return base64.urlsafe_b64encode(key)


def encrypt_value(value):
    """
    Cifra un valor usando Fernet (AES 128)
    """
    if not value:
        return value
    
    fernet = Fernet(get_encryption_key())
    encrypted = fernet.encrypt(value.encode())
    return encrypted.decode()


def decrypt_value(encrypted_value):
    """
    Descifra un valor cifrado
    """
    if not encrypted_value:
        return encrypted_value
    
    try:
        fernet = Fernet(get_encryption_key())
        decrypted = fernet.decrypt(encrypted_value.encode())
        return decrypted.decode()
    except Exception:
        # Si falla el descifrado, devolver None (puede ser valor antiguo sin cifrar)
        return None
