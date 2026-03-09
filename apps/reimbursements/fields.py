"""
Custom encrypted field for sensitive data.

Uses Fernet symmetric encryption from the cryptography library.
Works with Django 4.0+ (unlike the outdated django-fernet-fields package).
"""

from django.conf import settings
from django.db import models
from cryptography.fernet import Fernet, InvalidToken


def get_fernet():
    """Get Fernet instance using the configured encryption key."""
    key = getattr(settings, 'FIELD_ENCRYPTION_KEY', None)
    if not key:
        raise ValueError(
            "FIELD_ENCRYPTION_KEY not set in settings. "
            "Generate one with: python -c 'from cryptography.fernet import Fernet; print(Fernet.generate_key().decode())'"
        )
    # Ensure key is bytes
    if isinstance(key, str):
        key = key.encode()
    return Fernet(key)


class EncryptedCharField(models.CharField):
    """
    A CharField that encrypts its value before storing in the database.

    The value is encrypted using Fernet (AES-128-CBC with HMAC).
    In the database, values are stored as base64-encoded encrypted strings.
    In Python, values are decrypted automatically when accessed.
    """

    description = "An encrypted CharField"

    def __init__(self, *args, **kwargs):
        # Encrypted values are longer than the original
        # Fernet adds ~100 bytes of overhead, then base64 encoding adds ~33%
        kwargs['max_length'] = kwargs.get('max_length', 255) + 200
        super().__init__(*args, **kwargs)

    def get_prep_value(self, value):
        """Encrypt value before saving to database."""
        if value is None or value == '':
            return value

        # Convert to string if needed
        value = str(value)

        # Encrypt
        fernet = get_fernet()
        encrypted = fernet.encrypt(value.encode())
        return encrypted.decode()  # Store as string in DB

    def from_db_value(self, value, expression, connection):
        """Decrypt value when reading from database."""
        if value is None or value == '':
            return value

        try:
            fernet = get_fernet()
            decrypted = fernet.decrypt(value.encode())
            return decrypted.decode()
        except InvalidToken:
            # Value might not be encrypted (e.g., migrated data)
            # Or wrong key - return as-is but log warning
            import logging
            logging.warning(f"Could not decrypt field value - may be unencrypted or wrong key")
            return value

    def to_python(self, value):
        """Convert value to Python string."""
        if value is None:
            return value
        return str(value)
