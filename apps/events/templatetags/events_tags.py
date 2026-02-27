from django import template
from apps.events.models import Event

register = template.Library()


@register.inclusion_tag("events/_upcoming_events.html")
def upcoming_events(limit=3):
    """Display upcoming events in a compact list."""
    events = Event.objects.upcoming()[:limit]
    return {"events": events}


@register.inclusion_tag("events/_upcoming_events.html")
def next_events(limit=3):
    """Alias for upcoming_events (backwards compatibility)."""
    events = Event.objects.upcoming()[:limit]
    return {"events": events}
