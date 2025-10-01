from django.shortcuts import render, get_object_or_404
from django.utils import timezone
from django.db.models.functions import ExtractYear
from apps.events.models import *


def event_list(request):
    now = timezone.now()
    upcoming = Event.objects.filter(start__gte=now).order_by("start")
    past = (
        Event.objects.filter(start__lt=now)
        .annotate(year=ExtractYear("start"))
        .order_by("-start")
    )
    return render(request, "event_list.html", {"upcoming": upcoming, "past": past})


def event_detail(request, slug):
    event = get_object_or_404(Event, slug=slug)
    return render(request, "event_detail.html", {"event": event})
