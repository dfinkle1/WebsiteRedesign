from django.shortcuts import HttpResponse, render, get_object_or_404
from datetime import date, datetime, time, timedelta
from django.utils import timezone
from apps.workshops.models import OldWorkshop
from django.http import JsonResponse
from apps.core.models import *


def home(request):
    local_today = timezone.localdate()
    start_of_tomorrow = timezone.make_aware(
        datetime.combine(local_today + timedelta(days=1), time.min),
        timezone.get_current_timezone(),
    )
    qs = (
        OldWorkshop.objects.filter(workshopstartdate__gte=start_of_tomorrow)
        .filter(type=0)
        .only("workshopid", "workshopname", "workshopabbrev", "workshopstartdate")
        .order_by("workshopstartdate")[:11]
    )
    cache_key = f"home_workshops::{local_today.isoformat()}"
    return render(
        request,
        "home.html",
        {
            "old_workshops_after_today": qs,
            "home_cache_key": cache_key,
        },
    )


def donation_page(request):
    return render(request, "donate.html")


def filter_workshops(request):
    print("Filter workshops view called")
    current_date = date.today()
    workshops = OldWorkshop.objects.filter(
        workshopstartdate__date__lt=current_date
    ).order_by("-workshopstartdate")
    data = [
        {
            "workshopname": workshop.workshopname,
            "workshopstartdate": workshop.workshopstartdate.strftime("%b %d, %Y"),
            "workshopenddate": workshop.workshopenddate.strftime("%b %d, %Y"),
        }
        for workshop in workshops
    ]
    print(data[:5])
    return JsonResponse(data, safe=False)


# def home2(request):
#     current_date = date.today()
#     old_workshops_after_today = OldWorkshop.objects.filter(
#         workshopstartdate__date__gt=current_date
#     ).order_by("workshopstartdate")
#     # template = loader.get_template("workshop/index.html")
#     context = {"old_workshops_after_today": old_workshops_after_today}
#     print([workshop.workshopstartdate for workshop in old_workshops_after_today[:5]])
#     return render(request, "home.html", context)
