from django.shortcuts import HttpResponse
from datetime import date
from .models import OldWorkshop
from participants.models import Participant
from django.shortcuts import render
from django.http import JsonResponse


def home(request):
    current_date = date.today()
    old_workshops_after_today = OldWorkshop.objects.filter(
        workshopstartdate__date__gte=current_date
    ).order_by("workshopstartdate")
    # template = loader.get_template("workshop/index.html")
    context = {"old_workshops_after_today": old_workshops_after_today}
    print([workshop.workshopstartdate for workshop in old_workshops_after_today[:5]])

    return render(request, "base_index.html", context)


def home2(request):
    current_date = date.today()
    old_workshops_after_today = OldWorkshop.objects.filter(
        workshopstartdate__date__gt=current_date
    ).order_by("workshopstartdate")
    # template = loader.get_template("workshop/index.html")
    context = {"old_workshops_after_today": old_workshops_after_today}
    print([workshop.workshopstartdate for workshop in old_workshops_after_today[:5]])
    return render(request, "base.html", context)


def about(request):
    return render(request, "about.html")


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


def template1(request):
    return render(request, "template1.html")


def visiting(request):
    return render(request, "visiting.html")


def codeofconduct(request):
    return render(request, "code.html")


def visitingtemplate(request):
    return render(request, "visitingtemplate.html")


def template2(request):
    return render(request, "template2.html")
