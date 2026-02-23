from django.shortcuts import render, get_object_or_404
from django.db.models import Q
from django.core.paginator import Paginator
from django_ratelimit.decorators import ratelimit
from .models import Program
from programs.services import get_upcoming_workshops
from django.utils import timezone
from mysite.utils import get_safe_page


def program_page(request, code):
    program = get_object_or_404(Program, type=Program.ProgramType.WORKSHOP, code=code)
    now = timezone.now()

    # Check if user is enrolled or has applied
    user_enrollment = None
    if request.user.is_authenticated:
        try:
            person = request.user.profile.person
            from enrollments.models import Enrollment

            user_enrollment = Enrollment.objects.filter(
                person=person, workshop=program
            ).first()
        except AttributeError:
            pass

    return render(
        request,
        "program_page.html",
        {
            "program_page": program,
            "program": program,  # alias for cleaner template code
            "now": now,
            "user_enrollment": user_enrollment,
        },
    )


def list_of_workshops(request):
    workshops = Program.objects.filter(type=Program.ProgramType.WORKSHOP)
    context = {"workshops": workshops}
    return render(request, "workshop_list.html", context)


def upcoming_workshops(request):
    workshops = get_upcoming_workshops()
    now = timezone.now()
    return render(
        request,
        "programs/upcoming_workshops.html",
        {"workshops": workshops, "now": now},
    )


@ratelimit(key="ip", rate="60/m", method="GET", block=True)
def past_workshops(request):
    """
    Display past workshops with pagination, year filter, and search.
    Efficient: Uses LIMIT + OFFSET for pagination.
    Rate limited: 60 requests/minute per IP.
    Page capped: Maximum 100 pages to prevent bot abuse.
    """
    today = timezone.localdate()

    # Start with past workshops (end_date < today)
    workshops = Program.objects.filter(
        type=Program.ProgramType.WORKSHOP, end_date__lt=today
    )

    # Year filter (optional)
    year = request.GET.get("year")
    if year and year.isdigit():
        workshops = workshops.filter(start_date__year=int(year))

    # Search filter (optional) - searches title, organizers, description
    search = request.GET.get("search", "").strip()
    if search:
        workshops = workshops.filter(
            Q(title__icontains=search)
            | Q(organizer1__icontains=search)
            | Q(organizer2__icontains=search)
            | Q(description__icontains=search)
            | Q(code__icontains=search)
        )

    # Order by most recent first
    workshops = workshops.order_by("-end_date")

    # Pagination - 10 per page with safety cap
    paginator = Paginator(workshops, 10)
    workshops_page = get_safe_page(request, paginator)

    # Get available years for filter dropdown
    available_years = (
        Program.objects.filter(
            type=Program.ProgramType.WORKSHOP,
            end_date__lt=today,
            start_date__isnull=False,
        )
        .dates("start_date", "year", order="DESC")
        .values_list("start_date__year", flat=True)
        .distinct()
    )

    context = {
        "workshops": workshops_page,
        "available_years": available_years,
        "selected_year": year,
        "search_query": search,
    }

    return render(request, "programs/past_workshops.html", context)


def home(request):
    workshops = get_upcoming_workshops
    now = timezone.now()
    return render(request, "home.html", {"workshops": workshops, "now": now})
