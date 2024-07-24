from django.shortcuts import HttpResponse, render, get_object_or_404
from datetime import date
from apps.workshops.models import OldWorkshop
from participants.models import Participant
from django.http import JsonResponse
from apps.core.models import *


def render_my_model(request, obj):
    return render(
        request,
        "about.html",
        {
            "object": obj,
        },
    )


def my_model_detail(request, id):
    obj = get_object_or_404(MyModel)  # Get the object (here by id)
    request.toolbar.set_object(obj)  # Announce the object to the toolbar
    return render_my_model(request, MyModel)  # Same as preview rendering


def home(request):
    current_date = date.today()
    old_workshops_after_today = OldWorkshop.objects.filter(
        workshopstartdate__date__gte=current_date
    ).order_by("workshopstartdate")
    # template = loader.get_template("workshop/index.html")
    context = {
        "old_workshops_after_today": old_workshops_after_today,
    }

    return render(request, "core/home.html", context)


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


def home2(request):
    current_date = date.today()
    old_workshops_after_today = OldWorkshop.objects.filter(
        workshopstartdate__date__gt=current_date
    ).order_by("workshopstartdate")
    # template = loader.get_template("workshop/index.html")
    context = {"old_workshops_after_today": old_workshops_after_today}
    print([workshop.workshopstartdate for workshop in old_workshops_after_today[:5]])
    return render(request, "home.html", context)


def focused_collaborative_research(request):
    return render(request, "navbar/focusedcollaborativeresearch/focused-landing.html")


# navbar/joyfulmath
def joyfulmath_view(request):
    return render(request, "navbar/joyfulmath/joyfulmathematics.html")


#


def template_view(request):
    return render(request, "template1.html")


# navbar/about
def about_view(request):
    return render(request, "about.html")


# navbar/visiting


def codeofconduct(request):
    return render(request, "navbar/visiting/#codeofconduct")


#


# navbar/visiting
def visiting_view(request):
    return render(request, "navbar/visiting/visiting.html")


def resources_view(request):
    return render(request, "navbar/resources/resources.html")


# navbar/news


def news_view(request):
    return render(request, "navbar/news/news.html")


#
