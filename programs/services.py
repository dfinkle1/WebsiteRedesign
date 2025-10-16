from django.utils import timezone
from django.core.cache import cache
from datetime import datetime, timedelta, time
from .models import Program


def get_upcoming_workshops(limit=10, cache_seconds=600):
    cache_key = f"upcoming_workshops::{timezone.localdate().isoformat()}::{limit}"
    data = cache.get(cache_key)
    if data is not None:
        return data

    local_today = timezone.localdate()
    qs = (
        Program.objects.filter(
            type=Program.ProgramType.WORKSHOP, end_date__gte=local_today
        )
        .order_by("start_date")
        .only("title", "start_date", "title_abbreviation", "end_date", "code")[:12]
    )
    data = list(qs)
    cache.set(cache_key, data, cache_seconds)
    return data
