from django.shortcuts import render, get_object_or_404
from .models import Program
from programs.services import get_upcoming_workshops
from django.utils import timezone


def program_page(request, code):
    program_page = get_object_or_404(
        Program, type=Program.ProgramType.WORKSHOP, code=code
    )
    now = timezone.now()
    return render(
        request, "program_page.html", {"program_page": program_page, "now": now}
    )


def list_of_workshops(request):
    workshops = Program.objects.filter(type=Program.ProgramType.WORKSHOP)
    context = {"workshops": workshops}
    return render(request, "focused-landing.html", context)


def home(request):
    workshops = get_upcoming_workshops
    now = timezone.now()
    return render(request, "home.html", {"workshops": workshops, "now": now})
