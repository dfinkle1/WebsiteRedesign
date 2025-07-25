from django.core.exceptions import ValidationError


def validate_file_type(value):
    valid_extensions = ["pdf", "jpg", "jpeg", "png"]
    ext = value.name.split(".")[-1].lower()
    if ext not in valid_extensions:
        raise ValidationError("Invalid file type. Allowed types: PDF, JPG, PNG.")


def validate_file_size(value):
    limit_mb = 10
    if value.size > limit_mb * 1024 * 1024:
        raise ValidationError(f"File too large. Max size: {limit_mb} MB.")
