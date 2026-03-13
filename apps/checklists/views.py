from django.shortcuts import render, get_object_or_404, redirect
from django.contrib.auth.decorators import login_required
from django.contrib.admin.views.decorators import staff_member_required
from django.contrib import messages
from django.utils import timezone
from django.db.models import Q

from programs.models import Program
from .models import ProgramChecklist, ProgramChecklistItem
from .forms import ApplyTemplateForm, ChecklistItemUpdateForm, AddChecklistItemForm
from .services import apply_template_to_program, get_hub_data


# ---------------------------------------------------------------------------
# Program Checklist View
# The main coordinator view for one program's checklist.
# ---------------------------------------------------------------------------

@staff_member_required
def program_checklist(request, code):
    """
    Shows the full checklist for a single program.
    If no checklist exists yet, shows the Apply Template form.
    If it exists, shows all items grouped by category.
    """
    program = get_object_or_404(Program, code=code)
    checklist = getattr(program, "checklist", None)

    # Handle Apply Template form
    if request.method == "POST" and "apply_template" in request.POST:
        form = ApplyTemplateForm(request.POST)
        if form.is_valid():
            try:
                apply_template_to_program(
                    program=program,
                    template=form.cleaned_data["template"],
                    user=request.user,
                )
                messages.success(request, f"Checklist applied to {program.title}.")
                return redirect("checklists:program_checklist", code=code)
            except ValueError as e:
                messages.error(request, str(e))
    else:
        form = ApplyTemplateForm()

    context = {
        "program": program,
        "checklist": checklist,
        "form": form,
    }

    if checklist:
        from django.contrib.auth import get_user_model
        User = get_user_model()
        items = checklist.items.select_related("assigned_to").order_by("order", "category")
        grouped_items = [
            ("Pre-Program", items.filter(category="pre_program")),
            ("During Program", items.filter(category="during")),
            ("Post-Program", items.filter(category="post_program")),
        ]
        summary = checklist.completion_summary()
        staff_users = User.objects.filter(is_staff=True).order_by("first_name", "last_name")
        context.update({
            "grouped_items": grouped_items,
            "summary": summary,
            "health": checklist.health_status(),
            "overdue_count": checklist.overdue_count(),
            "staff_users": staff_users,
            "status_choices": ProgramChecklistItem.STATUS_CHOICES,
            "category_choices": ProgramChecklistItem.CATEGORY_CHOICES,
        })

    return render(request, "checklists/program_checklist.html", context)


# ---------------------------------------------------------------------------
# Update a single checklist item (status, assignee, notes, due date)
# ---------------------------------------------------------------------------

@staff_member_required
def update_checklist_item(request, item_pk):
    """
    POST-only view. Updates status/notes/assignee/due_date on one item.
    Redirects back to the program checklist.
    """
    item = get_object_or_404(ProgramChecklistItem, pk=item_pk)
    if request.method == "POST":
        form = ChecklistItemUpdateForm(request.POST, instance=item)
        if form.is_valid():
            updated = form.save(commit=False)
            if updated.status == "done" and not updated.completed_by:
                updated.completed_by = request.user
            updated.save()
            messages.success(request, f"'{item.title}' updated.")
        else:
            messages.error(request, "Could not update item. Check the form.")

    return redirect("checklists:program_checklist", code=item.checklist.program.code)


# ---------------------------------------------------------------------------
# Add a manual item to an existing checklist
# ---------------------------------------------------------------------------

@staff_member_required
def add_checklist_item(request, checklist_pk):
    """
    POST-only. Adds a one-off task to an existing program checklist.
    """
    checklist = get_object_or_404(ProgramChecklist, pk=checklist_pk)
    if request.method == "POST":
        form = AddChecklistItemForm(request.POST)
        if form.is_valid():
            item = form.save(commit=False)
            item.checklist = checklist
            item.template_item = None  # manually added, no template source
            # Place at end of existing items
            last_order = checklist.items.order_by("-order").values_list("order", flat=True).first()
            item.order = (last_order or 0) + 10
            item.save()
            messages.success(request, f"'{item.title}' added to checklist.")
        else:
            messages.error(request, "Could not add item. Check the form.")

    return redirect("checklists:program_checklist", code=checklist.program.code)


# ---------------------------------------------------------------------------
# My Tasks — personal view for the logged-in staff member
# ---------------------------------------------------------------------------

@login_required
def my_tasks(request):
    """
    Shows all checklist items assigned to the logged-in user,
    grouped by program, sorted by due date.
    """
    status_filter = request.GET.get("status", "")
    today = timezone.localdate()

    items = (
        ProgramChecklistItem.objects.filter(assigned_to=request.user)
        .exclude(status__in=["done", "na"])
        .select_related("checklist__program")
        .order_by("due_date", "checklist__program__start_date")
    )

    if status_filter:
        items = items.filter(status=status_filter)

    # Group by program
    grouped = {}
    for item in items:
        program = item.checklist.program
        if program.pk not in grouped:
            grouped[program.pk] = {"program": program, "items": []}
        grouped[program.pk]["items"].append(item)

    overdue_count = sum(1 for item in items if item.is_overdue)

    return render(request, "checklists/my_tasks.html", {
        "grouped": grouped.values(),
        "status_filter": status_filter,
        "overdue_count": overdue_count,
        "today": today,
        "status_choices": ProgramChecklistItem.STATUS_CHOICES,
    })


# ---------------------------------------------------------------------------
# Hub — all programs, category-level health overview
# ---------------------------------------------------------------------------

@staff_member_required
def hub(request):
    """
    Program Health Hub. Shows all current/upcoming programs grouped into
    labelled sections by type and phase (preparation vs follow-up).
    """
    today = timezone.localdate()

    programs = (
        Program.objects.filter(
            Q(start_date__gte=today) | Q(end_date__gte=today)
        )
        .order_by("start_date")
        .select_related("checklist")
    )

    hub_data = get_hub_data(programs)

    # Section definitions: (label, filter_fn)
    # "Preparation" = start_date in future; "Follow-up" = started but not yet fully ended
    def is_prep(row):
        sd = row["program"].start_date
        return sd is None or sd >= today

    def is_followup(row):
        sd = row["program"].start_date
        return sd is not None and sd < today

    SECTIONS = [
        ("Workshop Preparation",        lambda r: r["program"].type == "WORKSHOP"  and is_prep(r)),
        ("SQuaRE Preparation",          lambda r: r["program"].type == "SQUARE"    and is_prep(r) and (not r["program"].meeting_number or r["program"].meeting_number == 1)),
        ("SQuaRE Meetings Preparation", lambda r: r["program"].type == "SQUARE"    and is_prep(r) and r["program"].meeting_number and r["program"].meeting_number > 1),
        ("Virtual Workshop Preparation",lambda r: r["program"].type == "VWORKSHOP" and is_prep(r)),
        ("Virtual SQuaRE Preparation",  lambda r: r["program"].type == "VSQUARE"   and is_prep(r)),
        ("Workshop Follow-up",          lambda r: r["program"].type == "WORKSHOP"  and is_followup(r)),
        ("SQuaRE Follow-up",            lambda r: r["program"].type == "SQUARE"    and is_followup(r)),
        ("Virtual Workshop Follow-up",  lambda r: r["program"].type == "VWORKSHOP" and is_followup(r)),
        ("Virtual SQuaRE Follow-up",    lambda r: r["program"].type == "VSQUARE"   and is_followup(r)),
        ("Research Community",          lambda r: r["program"].type == "COMMUNITY"),
    ]

    grouped_hub_data = [
        {"label": label, "rows": [r for r in hub_data if fn(r)]}
        for label, fn in SECTIONS
    ]
    # Drop empty sections
    grouped_hub_data = [g for g in grouped_hub_data if g["rows"]]

    return render(request, "checklists/hub.html", {
        "grouped_hub_data": grouped_hub_data,
        "today": today,
    })


# ---------------------------------------------------------------------------
# All Tasks — flat filterable list for management
# ---------------------------------------------------------------------------

@staff_member_required
def all_tasks(request):
    """
    Every incomplete checklist item across all programs.
    Filterable by assignee and status.
    """
    assignee_filter = request.GET.get("assignee", "")
    status_filter = request.GET.get("status", "")

    from django.contrib.auth import get_user_model
    User = get_user_model()

    items = (
        ProgramChecklistItem.objects.exclude(status__in=["done", "na"])
        .select_related("checklist__program", "assigned_to")
        .order_by("due_date", "checklist__program__start_date")
    )

    if assignee_filter:
        items = items.filter(assigned_to_id=assignee_filter)
    if status_filter:
        items = items.filter(status=status_filter)

    staff_users = User.objects.filter(is_staff=True).order_by("first_name", "last_name")

    return render(request, "checklists/all_tasks.html", {
        "items": items,
        "staff_users": staff_users,
        "assignee_filter": assignee_filter,
        "status_filter": status_filter,
        "status_choices": ProgramChecklistItem.STATUS_CHOICES,
    })
