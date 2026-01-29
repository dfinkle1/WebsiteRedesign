from django.utils import timezone
from django.core.cache import cache
from django.forms.models import model_to_dict
from .models import *


def get_upcoming_workshops(limit=12, cache_seconds=600):
    today = timezone.localdate()
    cache_key = f"upcoming_workshops::{today.isoformat()}::{limit}"
    data = cache.get(cache_key)
    if data is not None:
        return data

    qs = (
        Program.objects.filter(type=Program.ProgramType.WORKSHOP, start_date__gte=today)
        .order_by("start_date")
        .only(
            "id",
            "code",
            "title",
            "abbreviation",
            "application_deadline",
            "start_date",
            "end_date",
            "description",
        )[:limit]
    )

    # Cache minimal payload (dicts), not full model instances
    fields = [
        "id",
        "code",
        "title",
        "abbreviation",
        "application_deadline",
        "start_date",
        "end_date",
        "description",
    ]
    data = [model_to_dict(p, fields=fields) for p in qs]
    cache.set(cache_key, data, cache_seconds)
    return data
