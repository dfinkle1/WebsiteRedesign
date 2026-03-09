"""
File upload validators for reimbursements.

Security-focused validation to prevent malicious file uploads.
"""

from django.core.exceptions import ValidationError


# Maximum file size in bytes (10MB)
MAX_FILE_SIZE = 10 * 1024 * 1024

# Allowed file extensions (lowercase)
ALLOWED_EXTENSIONS = {'pdf', 'jpg', 'jpeg', 'png'}

# Magic bytes for file type detection
FILE_SIGNATURES = {
    b'%PDF': 'pdf',
    b'\xff\xd8\xff': 'jpg',  # JPEG
    b'\x89PNG\r\n\x1a\n': 'png',
}


def validate_file_size(value):
    """Validate that uploaded file doesn't exceed maximum size."""
    if value.size > MAX_FILE_SIZE:
        max_mb = MAX_FILE_SIZE / (1024 * 1024)
        raise ValidationError(f"File too large. Max size: {max_mb:.0f} MB.")


def validate_file_type(value):
    """Validate that uploaded file has an allowed extension."""
    if not value.name:
        raise ValidationError("File must have a name.")

    parts = value.name.rsplit('.', 1)
    if len(parts) < 2:
        raise ValidationError("File must have an extension (e.g., .pdf, .jpg, .png).")

    ext = parts[1].lower()
    if ext not in ALLOWED_EXTENSIONS:
        raise ValidationError(
            f"Invalid file type '.{ext}'. Allowed types: PDF, JPG, PNG."
        )
    return ext


def validate_file_content(value):
    """
    Validate file content by checking magic bytes.

    This prevents attackers from uploading malicious files with fake extensions.
    """
    # Read the first 16 bytes for magic number detection
    value.seek(0)
    header = value.read(16)
    value.seek(0)  # Reset for later use

    if not header:
        raise ValidationError("File appears to be empty.")

    # Check against known file signatures
    detected_type = None
    for signature, file_type in FILE_SIGNATURES.items():
        if header.startswith(signature):
            detected_type = file_type
            break

    if detected_type is None:
        raise ValidationError(
            "File content could not be verified. Please upload a valid PDF, JPG, or PNG file."
        )

    return detected_type


def validate_uploaded_file(value):
    """
    Complete validation for uploaded files.

    Performs all security checks:
    - File size limit
    - Extension whitelist
    - Content type verification (magic bytes)
    - Extension/content match
    """
    # Check size
    validate_file_size(value)

    # Check extension
    ext = validate_file_type(value)

    # Check content matches extension (prevents polyglot attacks)
    content_type = validate_file_content(value)

    # Normalize jpeg -> jpg for comparison
    if ext == 'jpeg':
        ext = 'jpg'

    if ext != content_type:
        raise ValidationError(
            f"File extension '.{ext}' does not match file content. "
            "Please ensure the file is a valid PDF, JPG, or PNG."
        )
