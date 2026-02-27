from django.http import HttpResponse
from django.shortcuts import render, get_object_or_404
from django.db.models.functions import ExtractYear
from apps.events.models import Event


def event_list(request):
    """List all published events, separated into upcoming and past."""
    upcoming = Event.objects.upcoming()
    past = Event.objects.past().annotate(year=ExtractYear("start"))

    return render(
        request,
        "event_list.html",
        {
            "upcoming": upcoming,
            "past": past,
        },
    )


def event_detail(request, slug):
    """Single event detail page."""
    # Staff can preview draft events
    if request.user.is_staff:
        event = get_object_or_404(Event, slug=slug)
    else:
        event = get_object_or_404(Event, slug=slug, status=Event.Status.PUBLISHED)

    return render(request, "event_detail.html", {"event": event})


def event_ical(request, slug):
    """Generate iCal file for a single event."""
    event = get_object_or_404(Event, slug=slug, status=Event.Status.PUBLISHED)

    # Format dates for iCal
    start_str = event.start.strftime("%Y%m%dT%H%M%SZ")
    end_dt = event.end or event.start
    end_str = end_dt.strftime("%Y%m%dT%H%M%SZ")

    # Build iCal content
    ical_content = f"""BEGIN:VCALENDAR
VERSION:2.0
PRODID:-//AIM//Events//EN
BEGIN:VEVENT
UID:{event.slug}@aimath.org
DTSTART:{start_str}
DTEND:{end_str}
SUMMARY:{event.title}
DESCRIPTION:{event.short_summary or ''}
LOCATION:{event.full_address if not event.is_online else event.online_url}
URL:{request.build_absolute_uri(event.get_absolute_url())}
END:VEVENT
END:VCALENDAR"""

    response = HttpResponse(ical_content, content_type="text/calendar")
    response["Content-Disposition"] = f'attachment; filename="{event.slug}.ics"'
    return response
