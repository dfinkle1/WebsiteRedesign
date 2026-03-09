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
    workshops = get_upcoming_workshops()  # Fixed: was missing ()
    now = timezone.now()
    return render(request, "home.html", {"workshops": workshops, "now": now})


@ratelimit(key="ip", rate="60/m", method="GET", block=True)
def past_squares(request):
    """
    Display past SQuaREs (completed SQuaRE groups) with their participants.
    Shows only SQuaREs that have completed meeting 3 or later.
    """
    today = timezone.localdate()

    # Get root SQuaRE meetings that have a completed meeting 3+
    # A SQuaRE is "complete" when it has finished at least meeting 3
    from django.db.models import Exists, OuterRef

    # Subquery: check if this root has a subsequent meeting with number >= 3 that has ended
    has_completed_meeting_3_plus = Program.objects.filter(
        parent_square=OuterRef('pk'),
        meeting_number__gte=3,
        end_date__lt=today,
    )

    squares = Program.objects.filter(
        type=Program.ProgramType.SQUARE,
        parent_square__isnull=True,  # Only root meetings
    ).filter(
        # Either: root itself is meeting 3+ and ended, OR has a subsequent meeting 3+ that ended
        Q(meeting_number__gte=3, end_date__lt=today) | Q(Exists(has_completed_meeting_3_plus))
    )

    # Year filter (optional)
    year = request.GET.get("year")
    if year and year.isdigit():
        squares = squares.filter(start_date__year=int(year))

    # Search filter (optional)
    search = request.GET.get("search", "").strip()
    if search:
        squares = squares.filter(
            Q(title__icontains=search)
            | Q(description__icontains=search)
            | Q(code__icontains=search)
        )

    # Order by most recent first
    squares = squares.order_by("-end_date")

    # Pagination
    paginator = Paginator(squares, 10)
    squares_page = get_safe_page(request, paginator)

    # Get available years for filter dropdown
    available_years = (
        Program.objects.filter(
            type=Program.ProgramType.SQUARE,
            end_date__lt=today,
            parent_square__isnull=True,
            start_date__isnull=False,
        )
        .filter(
            Q(meeting_number__gte=3, end_date__lt=today) | Q(Exists(has_completed_meeting_3_plus))
        )
        .dates("start_date", "year", order="DESC")
        .values_list("start_date__year", flat=True)
        .distinct()
    )

    context = {
        "squares": squares_page,
        "available_years": available_years,
        "selected_year": year,
        "search_query": search,
    }

    return render(request, "programs/past_squares.html", context)


def square_detail(request, code):
    """
    Display details of a SQuaRE including all meetings and participants.
    """
    square = get_object_or_404(Program, type=Program.ProgramType.SQUARE, code=code)

    # Get the root SQuaRE
    root = square.square_root

    # Get all meetings in this SQuaRE group
    all_meetings = root.all_square_meetings

    # Get all unique participants across all meetings
    participants = root.get_all_square_participants()

    context = {
        "square": root,
        "all_meetings": all_meetings,
        "participants": participants,
        "participant_count": participants.count(),
    }

    return render(request, "programs/square_detail.html", context)
