from django import template
from django.utils import timezone
from apps.events.models import Event

register = template.Library()


@register.inclusion_tag("events/_next_events.html")
def next_events(limit=3):
    qs = Event.objects.filter(starts_at__gte=timezone.now()).order_by("starts_at")[
        :limit
    ]
    return {"events": qs}
