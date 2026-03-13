from datetime import timedelta
from .models import ProgramChecklist, ProgramChecklistItem


def apply_template_to_program(program, template, user):
    """
    Copies all items from a ChecklistTemplate onto a Program.
    Creates a ProgramChecklist and one ProgramChecklistItem per template item.

    Due dates are calculated from program.start_date + each item's
    default_days_before_start offset. Null if program has no start_date.

    Returns the created ProgramChecklist.
    Raises ValueError if the program already has a checklist.
    """
    if hasattr(program, "checklist"):
        raise ValueError(f"Program '{program.title}' already has a checklist.")

    checklist = ProgramChecklist.objects.create(
        program=program,
        template_used=template,
        created_by=user,
    )

    start_date = program.start_date
    items_to_create = []

    for template_item in template.items.order_by("order", "category"):
        due_date = None
        if start_date and template_item.default_days_before_start is not None:
            due_date = start_date + timedelta(days=template_item.default_days_before_start)

        items_to_create.append(
            ProgramChecklistItem(
                checklist=checklist,
                template_item=template_item,
                title=template_item.title,
                description=template_item.description,
                category=template_item.category,
                is_required=template_item.is_required,
                order=template_item.order,
                due_date=due_date,
                assigned_to=template_item.default_assignee,
                status="not_started",
            )
        )

    ProgramChecklistItem.objects.bulk_create(items_to_create)
    return checklist


def get_hub_data(programs):
    """
    For a queryset of programs, returns a list of dicts with checklist
    health data for the hub view. Programs without a checklist are included
    with checklist=None so the hub still shows them as grey.
    """
    checklists = (
        ProgramChecklist.objects.filter(program__in=programs)
        .prefetch_related("items")
        .select_related("program")
    )
    checklist_map = {c.program_id: c for c in checklists}

    results = []
    for program in programs:
        checklist = checklist_map.get(program.pk)
        if checklist:
            summary = checklist.completion_summary()
            health = checklist.health_status()
            overdue = checklist.overdue_count()
        else:
            summary = None
            health = "grey"
            overdue = 0

        results.append({
            "program": program,
            "checklist": checklist,
            "summary": summary,
            "health": health,
            "overdue": overdue,
        })

    return results
