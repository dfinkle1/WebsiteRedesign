from decimal import Decimal
from django.conf import settings
from django.db import models
from django.utils import timezone


# =============================================================================
# STAFF PROFILE
# =============================================================================


class StaffTimesheetProfile(models.Model):
    class StaffType(models.TextChoices):
        SALARY = "SALARY", "Salary (Monthly)"
        HOURLY = "HOURLY", "Hourly (Biweekly)"
        DIRECTOR = "DIRECTOR", "Director (Monthly)"

    user = models.OneToOneField(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name="timesheet_profile",
    )
    staff_type = models.CharField(max_length=8, choices=StaffType.choices)
    supervisor = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="supervised_staff",
        help_text="Supervisor with first-hand knowledge of the employee's work.",
    )
    title = models.CharField(max_length=255, blank=True)
    hire_date = models.DateField(null=True, blank=True)
    is_active = models.BooleanField(default=True)

    class Meta:
        verbose_name = "Staff Timesheet Profile"
        verbose_name_plural = "Staff Timesheet Profiles"

    def __str__(self):
        return f"{self.user.get_full_name() or self.user.username} ({self.get_staff_type_display()})"

    @property
    def supervisor_name(self):
        if self.supervisor:
            return self.supervisor.get_full_name() or self.supervisor.username
        return ""


# =============================================================================
# ACTIVITIES
# =============================================================================


class Activity(models.Model):
    class Classification(models.TextChoices):
        DIRECT = "DIRECT", "Direct"
        INDIRECT = "INDIRECT", "Indirect"
        LEAVE = "LEAVE", "Leave"
        UNALLOWABLE = "UNALLOWABLE", "Unallowable"

    name = models.CharField(max_length=255)
    default_grant_code = models.CharField(
        max_length=50,
        blank=True,
        help_text="Pre-filled grant code for this activity (e.g. DMS-2425344). Users can override per entry.",
    )
    classification = models.CharField(max_length=12, choices=Classification.choices)
    description_hint = models.CharField(
        max_length=255,
        blank=True,
        help_text="Placeholder text shown in the description field on the weekly entry form.",
    )
    is_active = models.BooleanField(default=True)
    is_preset = models.BooleanField(
        default=False,
        help_text="Preset activities appear automatically on every weekly entry form — staff cannot remove them.",
    )
    is_grant_addon = models.BooleanField(
        default=False,
        help_text="Grant addon activities are preset rows where the staff member specifies the grant code themselves.",
    )
    sort_order = models.PositiveSmallIntegerField(
        default=0,
        help_text="Controls display order on forms and PDFs. Lower numbers appear first.",
    )

    class Meta:
        ordering = ["sort_order", "name"]
        verbose_name = "Activity"
        verbose_name_plural = "Activities"

    def __str__(self):
        if self.default_grant_code:
            return f"{self.name} / {self.default_grant_code}"
        return self.name


# =============================================================================
# REPORTING CALENDAR
# =============================================================================


class ReportingPeriod(models.Model):
    class PeriodType(models.TextChoices):
        MONTHLY = "MONTHLY", "Monthly (4 weeks — Salary)"
        BIWEEKLY = "BIWEEKLY", "Biweekly (2 weeks — Hourly)"

    class StaffType(models.TextChoices):
        SALARY = "SALARY", "Salary"
        HOURLY = "HOURLY", "Hourly"

    label = models.CharField(
        max_length=100,
        help_text="Display label, e.g. 'March 2026' or 'Biweekly 03/08/26'.",
    )
    period_type = models.CharField(max_length=8, choices=PeriodType.choices)
    staff_type = models.CharField(max_length=8, choices=StaffType.choices)
    start_date = models.DateField()
    end_date = models.DateField()
    submission_deadline = models.DateTimeField(
        null=True,
        blank=True,
        help_text="Submitted timesheets can be edited until this date/time. Auto-set to period end + 3 days at 2:00 PM.",
    )
    is_locked = models.BooleanField(
        default=False,
        help_text="Hard lock — overrides the deadline and prevents all edits and submissions.",
    )

    class Meta:
        ordering = ["-start_date"]
        verbose_name = "Reporting Period"
        verbose_name_plural = "Reporting Periods"

    def __str__(self):
        return f"{self.label} ({self.start_date} – {self.end_date})"

    @property
    def edits_allowed(self):
        """True if submitted timesheets can still be edited (before submission deadline, not hard-locked)."""
        from django.utils import timezone
        if self.is_locked:
            return False
        if not self.submission_deadline:
            return True
        return timezone.now() < self.submission_deadline

    @property
    def week_count(self):
        return self.weeks.count()


class ReportingWeek(models.Model):
    period = models.ForeignKey(ReportingPeriod, on_delete=models.CASCADE, related_name="weeks")
    week_number = models.PositiveSmallIntegerField(help_text="1-indexed within the period.")
    start_date = models.DateField()
    end_date = models.DateField()
    due_date = models.DateField(
        null=True,
        blank=True,
        help_text="Soft deadline shown to staff. Not enforced as a hard block in v1.",
    )

    class Meta:
        ordering = ["period", "week_number"]
        unique_together = [("period", "week_number")]
        verbose_name = "Reporting Week"
        verbose_name_plural = "Reporting Weeks"

    def __str__(self):
        return f"{self.period.label} — Week {self.week_number} ({self.start_date} – {self.end_date})"


# =============================================================================
# WEEKLY TIMESHEETS
# =============================================================================


class WeeklyTimesheet(models.Model):
    class Status(models.TextChoices):
        DRAFT = "DRAFT", "Draft"
        SUBMITTED = "SUBMITTED", "Submitted"

    staff = models.ForeignKey(StaffTimesheetProfile, on_delete=models.CASCADE, related_name="timesheets")
    week = models.ForeignKey(ReportingWeek, on_delete=models.CASCADE, related_name="timesheets")
    status = models.CharField(max_length=9, choices=Status.choices, default=Status.DRAFT)
    zero_week_reason = models.CharField(
        max_length=255,
        blank=True,
        help_text="Required when submitting a week with zero total hours.",
    )
    submitted_at = models.DateTimeField(null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        unique_together = [("staff", "week")]
        ordering = ["week__start_date"]
        verbose_name = "Weekly Timesheet"
        verbose_name_plural = "Weekly Timesheets"

    def __str__(self):
        return f"{self.staff} — {self.week}"

    @property
    def total_hours(self):
        return sum(line.total_hours for line in self.lines.all())

    @property
    def is_zero_week(self):
        return self.total_hours == Decimal("0")

    def submit(self):
        """Mark as submitted. Caller is responsible for validation."""
        self.status = self.Status.SUBMITTED
        self.submitted_at = timezone.now()
        self.save(update_fields=["status", "submitted_at", "updated_at"])


class WeeklyTimesheetLine(models.Model):
    timesheet = models.ForeignKey(WeeklyTimesheet, on_delete=models.CASCADE, related_name="lines")
    activity = models.ForeignKey(Activity, on_delete=models.PROTECT, related_name="timesheet_lines")
    grant_code = models.CharField(
        max_length=50,
        blank=True,
        help_text="Grant code for this entry. Defaults to the activity's default grant code.",
    )
    hours_sun = models.DecimalField(max_digits=4, decimal_places=2, default=Decimal("0"))
    hours_mon = models.DecimalField(max_digits=4, decimal_places=2, default=Decimal("0"))
    hours_tue = models.DecimalField(max_digits=4, decimal_places=2, default=Decimal("0"))
    hours_wed = models.DecimalField(max_digits=4, decimal_places=2, default=Decimal("0"))
    hours_thu = models.DecimalField(max_digits=4, decimal_places=2, default=Decimal("0"))
    hours_fri = models.DecimalField(max_digits=4, decimal_places=2, default=Decimal("0"))
    hours_sat = models.DecimalField(max_digits=4, decimal_places=2, default=Decimal("0"))
    description = models.TextField(
        blank=True,
        help_text="Brief note about work performed this week for this activity.",
    )

    class Meta:
        unique_together = [("timesheet", "activity", "grant_code")]
        ordering = ["activity__sort_order", "activity__name"]
        verbose_name = "Timesheet Line"
        verbose_name_plural = "Timesheet Lines"

    def __str__(self):
        return f"{self.activity} — {self.total_hours}h"

    @property
    def total_hours(self):
        return (
            (self.hours_sun or Decimal("0"))
            + (self.hours_mon or Decimal("0"))
            + (self.hours_tue or Decimal("0"))
            + (self.hours_wed or Decimal("0"))
            + (self.hours_thu or Decimal("0"))
            + (self.hours_fri or Decimal("0"))
            + (self.hours_sat or Decimal("0"))
        )

    @property
    def day_hours(self):
        """Returns ordered list of (day_label, hours) for template rendering."""
        return [
            ("Sun", self.hours_sun),
            ("Mon", self.hours_mon),
            ("Tue", self.hours_tue),
            ("Wed", self.hours_wed),
            ("Thu", self.hours_thu),
            ("Fri", self.hours_fri),
            ("Sat", self.hours_sat),
        ]


# =============================================================================
# PERIOD REPORT
# =============================================================================


class PeriodReport(models.Model):
    class Status(models.TextChoices):
        PENDING = "PENDING", "Pending — weeks not yet complete"
        DESCRIBING = "DESCRIBING", "Ready — add descriptions before generating"
        GENERATED = "GENERATED", "Generated"

    staff = models.ForeignKey(StaffTimesheetProfile, on_delete=models.CASCADE, related_name="period_reports")
    period = models.ForeignKey(ReportingPeriod, on_delete=models.CASCADE, related_name="reports")
    status = models.CharField(max_length=10, choices=Status.choices, default=Status.PENDING)
    total_hours = models.DecimalField(max_digits=7, decimal_places=2, null=True, blank=True)
    # Snapshotted at generation time so historical PDFs are unaffected by profile changes
    supervisor_name_snapshot = models.CharField(max_length=255, blank=True)
    employee_title_snapshot = models.CharField(max_length=255, blank=True)
    employee_name_snapshot = models.CharField(max_length=255, blank=True)
    generated_at = models.DateTimeField(null=True, blank=True)

    class Meta:
        unique_together = [("staff", "period")]
        ordering = ["-period__start_date"]
        verbose_name = "Period Report"
        verbose_name_plural = "Period Reports"

    def __str__(self):
        return f"{self.staff} — {self.period}"

    @property
    def all_weeks_submitted(self):
        period_weeks = self.period.weeks.all()
        submitted_weeks = self.staff.timesheets.filter(
            week__in=period_weeks,
            status=WeeklyTimesheet.Status.SUBMITTED,
        ).count()
        return submitted_weeks == period_weeks.count()

    @property
    def outstanding_weeks(self):
        period_weeks = self.period.weeks.all()
        submitted_ids = self.staff.timesheets.filter(
            week__in=period_weeks,
            status=WeeklyTimesheet.Status.SUBMITTED,
        ).values_list("week_id", flat=True)
        return period_weeks.exclude(id__in=submitted_ids)


class PeriodReportLine(models.Model):
    """
    Immutable snapshot of one activity's contribution to a final period report.
    Populated during the describe step; frozen when the PDF is generated.
    """

    period_report = models.ForeignKey(PeriodReport, on_delete=models.CASCADE, related_name="lines")
    activity_name_snapshot = models.CharField(max_length=255)
    grant_code_snapshot = models.CharField(max_length=50, blank=True)
    classification_snapshot = models.CharField(max_length=12)
    total_hours = models.DecimalField(max_digits=7, decimal_places=2)
    percentage = models.DecimalField(max_digits=5, decimal_places=2)
    duties_description = models.TextField(blank=True)
    sort_order = models.PositiveSmallIntegerField(default=0)

    class Meta:
        ordering = ["sort_order", "activity_name_snapshot"]
        verbose_name = "Period Report Line"
        verbose_name_plural = "Period Report Lines"

    def __str__(self):
        return f"{self.activity_name_snapshot} — {self.total_hours}h ({self.percentage}%)"


# =============================================================================
# PDF SNAPSHOTS
# =============================================================================


class PDFSnapshot(models.Model):
    class PDFType(models.TextChoices):
        WEEKLY = "WEEKLY", "Weekly Report"
        FINAL = "FINAL", "Final Period Report"
        DIRECTOR = "DIRECTOR", "Director Period Report"

    period_report = models.ForeignKey(
        PeriodReport,
        on_delete=models.CASCADE,
        null=True,
        blank=True,
        related_name="pdfs",
    )
    timesheet = models.ForeignKey(
        WeeklyTimesheet,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="pdfs",
    )
    director_submission = models.ForeignKey(
        "DirectorPeriodSubmission",
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="pdfs",
    )
    pdf_type = models.CharField(max_length=8, choices=PDFType.choices)
    file = models.FileField(upload_to="timeeffort/pdfs/%Y/%m/")
    version = models.PositiveIntegerField(default=1)
    generated_at = models.DateTimeField(auto_now_add=True)
    generated_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
    )
    checksum = models.CharField(max_length=64, help_text="SHA-256 of the PDF file content.")

    class Meta:
        ordering = ["-generated_at"]
        verbose_name = "PDF Snapshot"
        verbose_name_plural = "PDF Snapshots"

    def __str__(self):
        return f"{self.get_pdf_type_display()} v{self.version} — {self.generated_at:%Y-%m-%d}"


# =============================================================================
# DIRECTOR EFFORT REPORTING
# =============================================================================


class AIMHoliday(models.Model):
    name = models.CharField(max_length=100)
    date = models.DateField(unique=True)

    class Meta:
        ordering = ["date"]
        verbose_name = "AIM Holiday"
        verbose_name_plural = "AIM Holidays"

    def __str__(self):
        return f"{self.name} ({self.date})"


class DirectorDefaultAllocation(models.Model):
    """Default percentages for a director, pre-filled on each new period form."""

    profile = models.OneToOneField(
        StaffTimesheetProfile,
        on_delete=models.CASCADE,
        related_name="director_defaults",
    )
    # Primary grant — locked on period entry, only editable here
    main_grant_code = models.CharField(max_length=50, blank=True, help_text="e.g. DMS-2425344")
    main_grant_pct = models.DecimalField(max_digits=5, decimal_places=2, default=Decimal("80.00"))
    # Additional direct grants (optional, pre-fill slots 1–4 on period entry)
    extra_grant_code_1 = models.CharField(max_length=50, blank=True)
    extra_grant_pct_1 = models.DecimalField(max_digits=5, decimal_places=2, default=Decimal("0"))
    extra_grant_code_2 = models.CharField(max_length=50, blank=True)
    extra_grant_pct_2 = models.DecimalField(max_digits=5, decimal_places=2, default=Decimal("0"))
    extra_grant_code_3 = models.CharField(max_length=50, blank=True)
    extra_grant_pct_3 = models.DecimalField(max_digits=5, decimal_places=2, default=Decimal("0"))
    extra_grant_code_4 = models.CharField(max_length=50, blank=True)
    extra_grant_pct_4 = models.DecimalField(max_digits=5, decimal_places=2, default=Decimal("0"))
    # Indirect defaults
    pct_administrative = models.DecimalField(max_digits=5, decimal_places=2, default=Decimal("0"))
    pct_other_activity = models.DecimalField(max_digits=5, decimal_places=2, default=Decimal("0"))
    pct_sick_personal = models.DecimalField(max_digits=5, decimal_places=2, default=Decimal("0"))
    pct_vacation = models.DecimalField(max_digits=5, decimal_places=2, default=Decimal("0"))
    pct_fundraising_pr = models.DecimalField(max_digits=5, decimal_places=2, default=Decimal("0"))
    pct_other_unallowable = models.DecimalField(max_digits=5, decimal_places=2, default=Decimal("0"))

    class Meta:
        verbose_name = "Director Default Allocation"
        verbose_name_plural = "Director Default Allocations"

    def __str__(self):
        return f"Defaults — {self.profile}"


class DirectorPeriodSubmission(models.Model):
    class Status(models.TextChoices):
        DRAFT = "DRAFT", "Draft"
        SUBMITTED = "SUBMITTED", "Submitted"

    staff = models.ForeignKey(StaffTimesheetProfile, on_delete=models.CASCADE, related_name="director_submissions")
    period = models.ForeignKey(ReportingPeriod, on_delete=models.CASCADE, related_name="director_submissions")
    status = models.CharField(max_length=9, choices=Status.choices, default=Status.DRAFT)
    submitted_at = models.DateTimeField(null=True, blank=True)
    employee_name_snapshot = models.CharField(max_length=255, blank=True)
    supervisor_name_snapshot = models.CharField(max_length=255, blank=True)
    employee_title_snapshot = models.CharField(max_length=255, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        unique_together = [("staff", "period")]
        ordering = ["-period__start_date"]
        verbose_name = "Director Period Submission"
        verbose_name_plural = "Director Period Submissions"

    def __str__(self):
        return f"{self.staff} — {self.period.label}"

    def submit(self):
        self.status = self.Status.SUBMITTED
        self.submitted_at = timezone.now()
        self.employee_name_snapshot = self.staff.user.get_full_name() or self.staff.user.username
        self.supervisor_name_snapshot = self.staff.supervisor_name
        self.employee_title_snapshot = self.staff.title
        self.save(update_fields=[
            "status", "submitted_at", "employee_name_snapshot",
            "supervisor_name_snapshot", "employee_title_snapshot", "updated_at",
        ])


class DirectorSubmissionLine(models.Model):
    class Category(models.TextChoices):
        DIRECT_MAIN = "DIRECT_MAIN", "Direct — Main Grant"
        DIRECT_EXTRA = "DIRECT_EXTRA", "Direct — Additional Grant"
        IND_ADMIN = "IND_ADMIN", "Administrative"
        IND_OTHER = "IND_OTHER", "Other Activity"
        IND_SICK = "IND_SICK", "Sick or Personal Day"
        IND_VACATION = "IND_VACATION", "Vacation"
        IND_HOLIDAY = "IND_HOLIDAY", "Employer Holiday"
        IND_FUNDRAISING = "IND_FUNDRAISING", "Fundraising / PR"
        IND_UNALLOWABLE = "IND_UNALLOWABLE", "Other Unallowable Activity"

    submission = models.ForeignKey(DirectorPeriodSubmission, on_delete=models.CASCADE, related_name="lines")
    category = models.CharField(max_length=16, choices=Category.choices)
    grant_code = models.CharField(max_length=50, blank=True)
    slot = models.PositiveSmallIntegerField(default=0, help_text="Ordering slot for extra grant rows (1–4).")
    percentage = models.DecimalField(max_digits=5, decimal_places=2, default=Decimal("0"))
    description = models.TextField(blank=True, help_text="Duties / work performed for this line.")
    is_locked = models.BooleanField(default=False, help_text="True for auto-calculated lines (employer holiday).")

    class Meta:
        ordering = ["slot", "category"]
        verbose_name = "Director Submission Line"
        verbose_name_plural = "Director Submission Lines"

    def __str__(self):
        return f"{self.get_category_display()} — {self.percentage}%"
