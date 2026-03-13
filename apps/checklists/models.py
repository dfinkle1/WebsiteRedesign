from django.db import models
from django.db.models import Count, Q
from django.contrib.auth import get_user_model
from django.utils import timezone

User = get_user_model()


class ChecklistTemplate(models.Model):
    """
    A reusable master checklist for a given program type.
    Admin creates one template per program type (Workshop, SQuaRE, etc.).
    When a coordinator applies a template to a program, items are copied
    from here into ProgramChecklistItem records.
    """

    PROGRAM_TYPE_CHOICES = [
        ("WORKSHOP", "Workshop"),
        ("SQUARE", "SQuaRE"),
        ("VSQUARE", "Virtual SQuaRE"),
        ("VWORKSHOP", "Virtual Workshop"),
        ("COMMUNITY", "Research Community"),
        ("GENERAL", "General (any program)"),
    ]

    name = models.CharField(max_length=200)
    program_type = models.CharField(max_length=20, choices=PROGRAM_TYPE_CHOICES)
    description = models.TextField(blank=True)
    is_active = models.BooleanField(default=True)
    order = models.PositiveIntegerField(default=0, db_index=True)
    created_by = models.ForeignKey(
        User, on_delete=models.SET_NULL, null=True, related_name="created_templates"
    )
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ["order", "program_type", "name"]
        verbose_name = "Checklist Template"
        verbose_name_plural = "Checklist Templates"

    def __str__(self):
        return f"{self.name} ({self.get_program_type_display()})"

    def item_count(self):
        return self.items.count()


class ChecklistTemplateItem(models.Model):
    """
    A single task definition inside a template.
    These are the master 30-40 items that get copied onto real programs.

    default_days_before_start is a signed integer:
        negative = N days before program start (e.g. -14 = 2 weeks before)
        positive = N days after program start (e.g. 3 = 3 days after start, post-program tasks)
        0        = due on program start date
        null     = no calculated due date
    """

    CATEGORY_CHOICES = [
        ("pre_program", "Pre-Program"),
        ("during", "During Program"),
        ("post_program", "Post-Program"),
    ]

    template = models.ForeignKey(ChecklistTemplate, on_delete=models.CASCADE, related_name="items")
    title = models.CharField(max_length=300)
    description = models.TextField(blank=True, help_text="Instructions or context for this task.")
    category = models.CharField(max_length=20, choices=CATEGORY_CHOICES, default="pre_program")
    default_days_before_start = models.IntegerField(
        null=True,
        blank=True,
        help_text="Negative = days before start. Positive = days after start. Blank = no auto due date.",
    )
    default_assignee = models.ForeignKey(
        User,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="default_template_items",
        help_text="Staff member to auto-assign when this template is applied to a program.",
        limit_choices_to={"is_staff": True},
    )
    is_required = models.BooleanField(default=False)
    order = models.PositiveIntegerField(default=0)

    class Meta:
        ordering = ["order", "category"]
        verbose_name = "Template Item"
        verbose_name_plural = "Template Items"

    def __str__(self):
        return f"{self.template.name} — {self.title}"


class ProgramChecklist(models.Model):
    """
    The live checklist container for a specific program.
    One per program. Created when a coordinator applies a template.
    Separate from Program so the checklist is optional and Program stays clean.
    """

    program = models.OneToOneField(
        "programs.Program",
        on_delete=models.CASCADE,
        related_name="checklist",
    )
    template_used = models.ForeignKey(
        ChecklistTemplate,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        help_text="Template this checklist was generated from. Kept for audit trail.",
    )
    created_by = models.ForeignKey(
        User, on_delete=models.SET_NULL, null=True, related_name="created_checklists"
    )
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        verbose_name = "Program Checklist"
        verbose_name_plural = "Program Checklists"

    def __str__(self):
        return f"Checklist — {self.program.title}"

    def completion_summary(self):
        """Returns total, done, pct overall and per category."""
        items = self.items.all()
        total = items.count()
        done = items.filter(status="done").count()
        pct = round((done / total) * 100) if total else 0

        by_category = (
            items.values("category")
            .annotate(total=Count("id"), done=Count("id", filter=Q(status="done")))
            .order_by("category")
        )

        return {
            "total": total,
            "done": done,
            "pct": pct,
            "by_category": {row["category"]: row for row in by_category},
        }

    def health_status(self):
        """
        Returns 'green', 'yellow', 'red', or 'grey'.
        Compares expected % complete (based on time elapsed) vs actual.
        """
        program = self.program
        if not program.start_date:
            return "grey"

        today = timezone.localdate()
        start = program.start_date

        if today >= start:
            summary = self.completion_summary()
            pct = summary["pct"]
            if pct >= 90:
                return "green"
            elif pct >= 60:
                return "yellow"
            return "red"

        created = self.created_at.date()
        days_total = (start - created).days
        if days_total <= 0:
            return "grey"

        days_elapsed = (today - created).days
        expected_pct = days_elapsed / days_total
        summary = self.completion_summary()
        actual_pct = summary["pct"] / 100

        if actual_pct >= expected_pct:
            return "green"
        elif actual_pct >= expected_pct - 0.15:
            return "yellow"
        return "red"

    def overdue_count(self):
        return self.items.filter(
            due_date__lt=timezone.localdate()
        ).exclude(status="done").count()

    def sync_from_template(self):
        """
        Adds any template items not yet present in this checklist.
        Safe: never modifies or deletes existing items.
        Returns the count of newly added items.
        """
        if not self.template_used:
            return 0

        from datetime import timedelta
        existing_template_ids = set(
            self.items.filter(template_item__isnull=False)
            .values_list("template_item_id", flat=True)
        )
        start_date = self.program.start_date
        new_items = []

        for ti in self.template_used.items.order_by("order", "category"):
            if ti.pk in existing_template_ids:
                continue
            due_date = None
            if start_date and ti.default_days_before_start is not None:
                due_date = start_date + timedelta(days=ti.default_days_before_start)
            new_items.append(
                ProgramChecklistItem(
                    checklist=self,
                    template_item=ti,
                    title=ti.title,
                    description=ti.description,
                    category=ti.category,
                    is_required=ti.is_required,
                    order=ti.order,
                    due_date=due_date,
                    assigned_to=ti.default_assignee,
                    status="not_started",
                )
            )

        if new_items:
            ProgramChecklistItem.objects.bulk_create(new_items)
        return len(new_items)


class ProgramChecklistItem(models.Model):
    """
    A single live task for a specific program.
    Copied from ChecklistTemplateItem when a checklist is applied.
    Title/description are stored as editable copies so that editing
    a template later does not silently change existing programs.
    """

    STATUS_CHOICES = [
        ("not_started", "Not Started"),
        ("in_progress", "In Progress"),
        ("blocked", "Blocked"),
        ("done", "Done"),
        ("na", "N/A"),
    ]

    CATEGORY_CHOICES = ChecklistTemplateItem.CATEGORY_CHOICES

    checklist = models.ForeignKey(ProgramChecklist, on_delete=models.CASCADE, related_name="items")
    template_item = models.ForeignKey(
        ChecklistTemplateItem,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        help_text="Source template item. Null if manually added by staff.",
    )

    # Editable copies — denormalized from template on creation
    title = models.CharField(max_length=300)
    description = models.TextField(blank=True)
    category = models.CharField(max_length=20, choices=CATEGORY_CHOICES, default="pre_program")
    is_required = models.BooleanField(default=False)
    order = models.PositiveIntegerField(default=0)

    # Live fields set by coordinator / staff
    assigned_to = models.ForeignKey(
        User,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="assigned_checklist_items",
    )
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default="not_started")
    due_date = models.DateField(null=True, blank=True)
    notes = models.TextField(blank=True)

    # Completion audit
    completed_at = models.DateTimeField(null=True, blank=True)
    completed_by = models.ForeignKey(
        User,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="completed_checklist_items",
    )
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ["order", "category"]
        verbose_name = "Checklist Item"
        verbose_name_plural = "Checklist Items"

    def __str__(self):
        return f"{self.checklist.program.title} — {self.title}"

    def save(self, *args, **kwargs):
        if self.status == "done" and not self.completed_at:
            self.completed_at = timezone.now()
        elif self.status != "done":
            self.completed_at = None
            self.completed_by = None
        super().save(*args, **kwargs)

    @property
    def is_overdue(self):
        return bool(
            self.due_date
            and self.due_date < timezone.localdate()
            and self.status not in ("done", "na")
        )

    @property
    def days_until_due(self):
        if not self.due_date:
            return None
        return (self.due_date - timezone.localdate()).days

    @property
    def urgency_class(self):
        """CSS class for color-coded urgency. Used in templates."""
        if self.status in ("done", "na"):
            return "urgency-done"
        if not self.due_date:
            return "urgency-none"
        days = self.days_until_due
        if days < 0:
            return "urgency-overdue"
        elif days <= 3:
            return "urgency-urgent"
        elif days <= 7:
            return "urgency-soon"
        return "urgency-ok"
