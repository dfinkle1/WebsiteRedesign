from django.db import transaction
from django.utils import timezone


def generate_receipt_number(donation) -> str:
    """
    Generates a unique receipt number: AIM-{YEAR}-{N:05d}
    Example: AIM-2026-00042

    Uses select_for_update() inside a transaction to prevent duplicate numbers
    if the same webhook fires twice concurrently (PayPal can do this).
    """
    year = timezone.now().year
    prefix = f"AIM-{year}-"

    with transaction.atomic():
        count = (
            donation.__class__.objects.select_for_update()
            .filter(receipt_number__startswith=prefix)
            .count()
        )
        return f"{prefix}{count + 1:05d}"
