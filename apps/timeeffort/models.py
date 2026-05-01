from datetime import timedelta, datetime, time
from decimal import Decimal

from django.conf import settings
from django.db import models
from django.utils import timezone


# =============================================================================
# STAFF PROFILE
# =============================================================================


class StaffTimesheetProfile(models.Model):
    class StaffType(models.TextChoices):
        SALARY = "SALARY", "Salary"
        HOURLY = "HOURLY", "Hourly"
        DIRECTOR = "DIRECTOR", "Director"

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

    @property
    def is_hourly(self):
        return self.staff_type == self.StaffType.HOURLY

    @property
    def is_salary(self):
        return self.staff_type == self.StaffType.SALARY

    @property
    def is_director(self):
        return self.staff_type == self.StaffType.DIRECTOR

    @property
    def submits_weekly_timesheets(self):
        """Hourly and Salary staff submit weekly timesheets. Directors do not."""
        return self.staff_type in (self.StaffType.HOURLY, self.StaffType.SALARY)

    @property
    def report_period_length(self):
        """Number of 14-day periods covered per period report: 1 for hourly, 2 for salary/director."""
        return 1 if self.is_hourly else 2


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
    valid_from = models.DateField(
        null=True,
        blank=True,
        help_text="First date this activity (grant) is valid. Leave blank for no start restriction.",
    )
    valid_to = models.DateField(
        null=True,
        blank=True,
        help_text="Last date this activity (grant) is valid. Leave blank for no end restriction.",
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
    is_holiday_activity = models.BooleanField(
        default=False,
        help_text="Mark exactly one activity as the AIM Holiday activity. It will be auto-inserted at 8h on holidays.",
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

    def is_valid_for_week(self, week_start, week_end):
        """Return True if this activity is valid for any day in the given week range."""
        if self.valid_from and self.valid_from > week_end:
            return False
        if self.valid_to and self.valid_to < week_start:
            return False
        return True


# =============================================================================
# AIM HOLIDAYS
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


# =============================================================================
# REPORTING CALENDAR
# =============================================================================


class ReportingCalendar(models.Model):
    """
    Singleton anchor that drives all period generation.

    All ReportingPeriods are 14 days (biweekly).
    Hourly staff submit one period report per period.
    Salary and Director staff submit one period report per two consecutive
    periods (28-day window). The anchor_start_date must be the start of a
    salary/director 28-day window — i.e. period_index 0 is always the first
    half of a salary month.
    """

    anchor_start_date = models.DateField(
        unique=True,
        help_text=(
            "Start date of the first (or anchor) biweekly period. "
            "Must fall on a Sunday or the organisation's standard week-start day. "
            "All future and past periods are calculated from this date."
        ),
    )
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        verbose_name = "Reporting Calendar"
        verbose_name_plural = "Reporting Calendar"

    def __str__(self):
        return f"Reporting Calendar (anchor: {self.anchor_start_date})"

    def save(self, *args, **kwargs):
        if not self.pk and ReportingCalendar.objects.exists():
            raise ValueError("Only one ReportingCalendar may exist.")
        super().save(*args, **kwargs)

    # ------------------------------------------------------------------
    # Period index helpers
    # ------------------------------------------------------------------

    def period_index_for_date(self, d):
        """
        Return the period_index for the period containing date d.
        period_index 0 = anchor period. Negative = before anchor.
        """
        delta = (d - self.anchor_start_date).days
        return delta // 14

    # ------------------------------------------------------------------
    # Generation
    # ------------------------------------------------------------------

    def generate_periods(self, months_back=24, months_forward=13):
        """
        Generate ReportingPeriod + ReportingWeek rows from months_back
        28-day months before the anchor through months_forward 28-day
        months ahead of the anchor.

        Safe to call multiple times — skips date ranges that already exist.

        Returns (created_count, skipped_count).
        """
        # Each 28-day salary month = 2 biweekly periods
        periods_back = months_back * 2
        periods_forward = months_forward * 2
        total_periods = periods_back + periods_forward

        created = 0
        skipped = 0

        for i in range(total_periods):
            # period_index relative to anchor (can be negative for past periods)
            period_index = -periods_back + i
            period_start = self.anchor_start_date + timedelta(days=period_index * 14)
            period_end = period_start + timedelta(days=13)

            label = (
                f"{period_start.strftime('%b %-d')} – "
                f"{period_end.strftime('%b %-d, %Y')}"
            )

            # submission_deadline = period end + 3 days at 14:00 local
            deadline_naive = datetime.combine(
                period_end + timedelta(days=3), time(14, 0)
            )
            deadline = timezone.make_aware(deadline_naive)

            period, was_created = ReportingPeriod.objects.get_or_create(
                calendar=self,
                period_index=period_index,
                defaults={
                    "start_date": period_start,
                    "end_date": period_end,
                    "label": label,
                    "submission_deadline": deadline,
                },
            )

            if was_created:
                created += 1
                for w in range(2):
                    week_start = period_start + timedelta(days=w * 7)
                    week_end = week_start + timedelta(days=6)
                    ReportingWeek.objects.get_or_create(
                        period=period,
                        week_number=w + 1,
                        defaults={
                            "start_date": week_start,
                            "end_date": week_end,
                        },
                    )
            else:
                skipped += 1

        return created, skipped


# =============================================================================
# REPORTING PERIOD  (always 14 days)
# =============================================================================


class ReportingPeriod(models.Model):
    """
    A single 14-day biweekly period.

    period_index:
      0  = anchor period (first half of salary month 1)
      1  = second half of salary month 1
      2  = first half of salary month 2
      -1 = second half of the salary month preceding the anchor
      -2 = first half of the salary month preceding the anchor
      etc.

    Salary/Director period reports always anchor on even period_index values.
    Hourly period reports can use any period_index.
    """

    calendar = models.ForeignKey(
        ReportingCalendar,
        on_delete=models.PROTECT,
        related_name="periods",
        null=True,
        blank=True,
        help_text="Leave blank only for legacy periods created before the calendar was set up.",
    )
    period_index = models.IntegerField(
        default=0,
        help_text="Offset in 14-day units from the calendar anchor date. 0 = anchor period.",
    )
    start_date = models.DateField(unique=True)
    end_date = models.DateField(unique=True)
    label = models.CharField(
        max_length=100,
        help_text="Auto-generated display label, e.g. 'Jan 11 – Jan 24, 2026'.",
    )
    submission_deadline = models.DateTimeField(
        null=True,
        blank=True,
        help_text="Auto-set to period end + 3 days at 2:00 PM. Submitted timesheets can be edited until this time.",
    )
    is_locked = models.BooleanField(
        default=False,
        help_text="Hard lock — overrides the deadline and prevents all edits and submissions.",
    )

    class Meta:
        ordering = ["-start_date"]
        unique_together = [("calendar", "period_index")]
        verbose_name = "Reporting Period"
        verbose_name_plural = "Reporting Periods"

    def __str__(self):
        return f"{self.label} ({self.start_date} – {self.end_date})"

    # ------------------------------------------------------------------
    # Salary / Director pairing helpers
    # ------------------------------------------------------------------

    @property
    def is_salary_month_start(self):
        """True when this period is the first of a 28-day salary/director window."""
        return self.period_index % 2 == 0

    @property
    def salary_month_label(self):
        """
        Label covering this period + the next (28 days).
        For display on salary/director reports.
        """
        try:
            next_p = ReportingPeriod.objects.get(
                calendar=self.calendar,
                period_index=self.period_index + 1,
            )
            return (
                f"{self.start_date.strftime('%b %-d')} – "
                f"{next_p.end_date.strftime('%b %-d, %Y')}"
            )
        except ReportingPeriod.DoesNotExist:
            return self.label

    @property
    def edits_allowed(self):
        if self.is_locked:
            return False
        if not self.submission_deadline:
            return True
        return timezone.now() < self.submission_deadline

    @property
    def week_count(self):
        return self.weeks.count()


# =============================================================================
# REPORTING WEEK  (always 7 days, two per period)
# =============================================================================


class ReportingWeek(models.Model):
    period = models.ForeignKey(
        ReportingPeriod,
        on_delete=models.CASCADE,
        related_name="weeks",
    )
    week_number = models.PositiveSmallIntegerField(
        help_text="1 or 2 within the period.",
    )
    start_date = models.DateField(unique=True)
    end_date = models.DateField(unique=True)
    due_date = models.DateField(
        null=True,
        blank=True,
        help_text="Soft deadline shown to staff for this specific week.",
    )

    class Meta:
        ordering = ["start_date"]
        unique_together = [("period", "week_number")]
        verbose_name = "Reporting Week"
        verbose_name_plural = "Reporting Weeks"

    def __str__(self):
        return f"{self.period.label} — Week {self.week_number} ({self.start_date} – {self.end_date})"


# =============================================================================
# WEEKLY TIMESHEETS  (Salary + Hourly only; Directors skip this layer)
# =============================================================================


class WeeklyTimesheet(models.Model):
    class Status(models.TextChoices):
        DRAFT = "DRAFT", "Draft"
        SUBMITTED = "SUBMITTED", "Submitted"

    staff = models.ForeignKey(
        StaffTimesheetProfile,
        on_delete=models.CASCADE,
        related_name="timesheets",
    )
    week = models.ForeignKey(
        ReportingWeek,
        on_delete=models.CASCADE,
        related_name="timesheets",
    )
    status = models.CharField(
        max_length=9,
        choices=Status.choices,
        default=Status.DRAFT,
    )
    # Supervisor sign-off — independent of status; visible to head processor
    # immediately once status = SUBMITTED regardless of whether supervisor has signed.
    supervisor_approved_at = models.DateTimeField(null=True, blank=True)
    supervisor_approved_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="supervisor_approved_timesheets",
    )
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

    # ------------------------------------------------------------------
    # Computed properties
    # ------------------------------------------------------------------

    @property
    def total_hours(self):
        return sum(line.total_hours for line in self.lines.all())

    @property
    def is_zero_week(self):
        return self.total_hours == Decimal("0")

    @property
    def supervisor_has_approved(self):
        return self.supervisor_approved_at is not None

    # ------------------------------------------------------------------
    # State transitions
    # ------------------------------------------------------------------

    def submit(self):
        """Mark as submitted. Caller is responsible for validation."""
        self.status = self.Status.SUBMITTED
        self.submitted_at = timezone.now()
        self.save(update_fields=["status", "submitted_at", "updated_at"])

    def supervisor_approve(self, approved_by):
        """Record supervisor sign-off. Does not block payroll visibility."""
        self.supervisor_approved_at = timezone.now()
        self.supervisor_approved_by = approved_by
        self.save(update_fields=["supervisor_approved_at", "supervisor_approved_by", "updated_at"])

    # ------------------------------------------------------------------
    # Factory — creates the timesheet and auto-inserts holiday lines
    # ------------------------------------------------------------------

    @classmethod
    def create_with_holidays(cls, staff, week):
        """
        Get or create a WeeklyTimesheet for this staff/week.
        On creation, auto-inserts 8-hour lines for any AIM holidays
        that fall within the week.
        """
        timesheet, created = cls.objects.get_or_create(staff=staff, week=week)

        if created:
            try:
                holiday_activity = Activity.objects.get(
                    is_holiday_activity=True,
                    is_active=True,
                )
            except Activity.DoesNotExist:
                return timesheet

            # Map Python weekday (Mon=0 … Sun=6) to hours field name
            day_field = {
                6: "hours_sun",
                0: "hours_mon",
                1: "hours_tue",
                2: "hours_wed",
                3: "hours_thu",
                4: "hours_fri",
                5: "hours_sat",
            }

            holidays = AIMHoliday.objects.filter(
                date__range=[week.start_date, week.end_date]
            )

            for holiday in holidays:
                field = day_field.get(holiday.date.weekday())
                if field:
                    WeeklyTimesheetLine.objects.get_or_create(
                        timesheet=timesheet,
                        activity=holiday_activity,
                        grant_code="",
                        defaults={field: Decimal("8")},
                    )

        return timesheet


class WeeklyTimesheetLine(models.Model):
    timesheet = models.ForeignKey(
        WeeklyTimesheet,
        on_delete=models.CASCADE,
        related_name="lines",
    )
    activity = models.ForeignKey(
        Activity,
        on_delete=models.PROTECT,
        null=True,
        blank=True,
        related_name="timesheet_lines",
    )
    custom_activity_name = models.CharField(
        max_length=255,
        blank=True,
        help_text="Free-text activity name for custom grant rows (salary staff only).",
    )
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
        ordering = ["activity__sort_order", "activity__name", "custom_activity_name"]
        verbose_name = "Timesheet Line"
        verbose_name_plural = "Timesheet Lines"

    def __str__(self):
        name = str(self.activity) if self.activity else (self.custom_activity_name or "Custom")
        return f"{name} — {self.total_hours}h"

    @property
    def total_hours(self):
        return sum([
            self.hours_sun or Decimal("0"),
            self.hours_mon or Decimal("0"),
            self.hours_tue or Decimal("0"),
            self.hours_wed or Decimal("0"),
            self.hours_thu or Decimal("0"),
            self.hours_fri or Decimal("0"),
            self.hours_sat or Decimal("0"),
        ])

    @property
    def day_hours(self):
        """Ordered list of (day_label, hours) for template rendering."""
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
# PERIOD REPORT  (unified for all staff types)
# =============================================================================


class PeriodReport(models.Model):
    """
    A period-level effort report. Covers:
      - Hourly staff:          one 14-day period  (period_index N, any N)
      - Salary staff:          two 14-day periods (period_index N where N is even)
      - Director staff:        two 14-day periods (period_index N where N is even)

    submission_type = HOURS → hours are rolled up from WeeklyTimesheets;
                              percentage is calculated from hours totals.
    submission_type = PCT   → staff enter percentages directly (Director workflow);
                              hours fields are null.

    Visibility rule: once status = SUBMITTED, the head processor can see and
    act on the report regardless of whether the supervisor has signed off.
    Supervisor approval is a stamp, not a gate.
    """

    class Status(models.TextChoices):
        DRAFT = "DRAFT", "Draft"
        SUBMITTED = "SUBMITTED", "Submitted"
        SUPERVISOR_APPROVED = "SUPV_APPR", "Supervisor Approved"
        PROCESSED = "PROCESSED", "Processed"

    class SubmissionType(models.TextChoices):
        HOURS = "HOURS", "Hours Based (Salary / Hourly)"
        PCT = "PCT", "Percentage Based (Director)"

    staff = models.ForeignKey(
        StaffTimesheetProfile,
        on_delete=models.CASCADE,
        related_name="period_reports",
    )
    # For hourly: the single 14-day period being reported.
    # For salary/director: the FIRST (even period_index) of the 28-day pair.
    period = models.ForeignKey(
        ReportingPeriod,
        on_delete=models.CASCADE,
        related_name="reports",
    )
    submission_type = models.CharField(
        max_length=5,
        choices=SubmissionType.choices,
        help_text="HOURS for salary/hourly (rolled up from timesheets). PCT for directors (entered directly).",
    )
    status = models.CharField(
        max_length=9,
        choices=Status.choices,
        default=Status.DRAFT,
    )

    # Supervisor sign-off
    supervisor_approved_at = models.DateTimeField(null=True, blank=True)
    supervisor_approved_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="supervisor_approved_reports",
    )

    # Head-processor sign-off
    processed_at = models.DateTimeField(null=True, blank=True)
    processed_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="processed_reports",
    )

    # Snapshotted at generation time so historical PDFs are unaffected by profile changes
    total_hours = models.DecimalField(
        max_digits=7,
        decimal_places=2,
        null=True,
        blank=True,
        help_text="Null for PCT-based director reports.",
    )
    supervisor_name_snapshot = models.CharField(max_length=255, blank=True)
    employee_title_snapshot = models.CharField(max_length=255, blank=True)
    employee_name_snapshot = models.CharField(max_length=255, blank=True)
    generated_at = models.DateTimeField(null=True, blank=True)
    submitted_at = models.DateTimeField(null=True, blank=True)

    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        unique_together = [("staff", "period")]
        ordering = ["-period__start_date"]
        verbose_name = "Period Report"
        verbose_name_plural = "Period Reports"

    def __str__(self):
        return f"{self.staff} — {self.period.label}"

    # ------------------------------------------------------------------
    # Coverage helpers
    # ------------------------------------------------------------------

    @property
    def effective_end_date(self):
        """Last date covered by this report (end of the 28-day window for salary/director)."""
        if self.staff.is_hourly:
            return self.period.end_date
        try:
            next_period = ReportingPeriod.objects.get(
                calendar=self.period.calendar,
                period_index=self.period.period_index + 1,
            )
            return next_period.end_date
        except ReportingPeriod.DoesNotExist:
            return self.period.end_date

    @property
    def covered_periods(self):
        """QuerySet of ReportingPeriod objects this report covers (1 for hourly, 2 for salary/director)."""
        if self.staff.is_hourly:
            return ReportingPeriod.objects.filter(pk=self.period_id)
        return ReportingPeriod.objects.filter(
            calendar=self.period.calendar,
            period_index__in=[self.period.period_index, self.period.period_index + 1],
        )

    @property
    def covered_weeks(self):
        return ReportingWeek.objects.filter(period__in=self.covered_periods)

    # ------------------------------------------------------------------
    # Readiness checks (hours-based only)
    # ------------------------------------------------------------------

    @property
    def all_weeks_submitted(self):
        if self.submission_type == self.SubmissionType.PCT:
            return True  # Directors have no weekly timesheets
        weeks = self.covered_weeks
        submitted_count = self.staff.timesheets.filter(
            week__in=weeks,
            status=WeeklyTimesheet.Status.SUBMITTED,
        ).count()
        return submitted_count == weeks.count()

    @property
    def outstanding_weeks(self):
        if self.submission_type == self.SubmissionType.PCT:
            return ReportingWeek.objects.none()
        submitted_ids = self.staff.timesheets.filter(
            week__in=self.covered_weeks,
            status=WeeklyTimesheet.Status.SUBMITTED,
        ).values_list("week_id", flat=True)
        return self.covered_weeks.exclude(id__in=submitted_ids)

    # ------------------------------------------------------------------
    # State transitions
    # ------------------------------------------------------------------

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

    def supervisor_approve(self, approved_by):
        self.supervisor_approved_at = timezone.now()
        self.supervisor_approved_by = approved_by
        self.status = self.Status.SUPERVISOR_APPROVED
        self.save(update_fields=[
            "supervisor_approved_at", "supervisor_approved_by", "status", "updated_at",
        ])

    def mark_processed(self, processed_by):
        self.processed_at = timezone.now()
        self.processed_by = processed_by
        self.status = self.Status.PROCESSED
        self.save(update_fields=[
            "processed_at", "processed_by", "status", "updated_at",
        ])

    # ------------------------------------------------------------------
    # Copy
    # ------------------------------------------------------------------

    def copy_from(self, source_report):
        """
        Copy all PeriodReportLines from source_report into this report.
        Clears any existing lines first. Report is left in DRAFT so
        the user can adjust before submitting.

        For HOURS-based reports, hours are intentionally not copied —
        they will be recalculated from the timesheets of this period.
        Only duties_description and sort_order are copied, giving the
        user a description template to edit.

        For PCT-based (director) reports, percentages and descriptions
        are copied in full.
        """
        self.lines.all().delete()
        for source_line in source_report.lines.order_by("sort_order"):
            PeriodReportLine.objects.create(
                period_report=self,
                activity_name_snapshot=source_line.activity_name_snapshot,
                grant_code_snapshot=source_line.grant_code_snapshot,
                classification_snapshot=source_line.classification_snapshot,
                # For HOURS reports, hours recalculated at report init time
                total_hours=source_line.total_hours if self.submission_type == self.SubmissionType.PCT else None,
                percentage=source_line.percentage if self.submission_type == self.SubmissionType.PCT else Decimal("0"),
                duties_description=source_line.duties_description,
                sort_order=source_line.sort_order,
            )


class PeriodReportLine(models.Model):
    """
    One activity row in a period report.

    For HOURS reports: total_hours is rolled up from WeeklyTimesheetLines;
                       percentage is calculated from hours.
    For PCT reports:   percentage is entered directly by the director;
                       total_hours is null.
    """

    period_report = models.ForeignKey(
        PeriodReport,
        on_delete=models.CASCADE,
        related_name="lines",
    )
    activity_name_snapshot = models.CharField(max_length=255)
    grant_code_snapshot = models.CharField(max_length=50, blank=True)
    classification_snapshot = models.CharField(max_length=12)
    total_hours = models.DecimalField(
        max_digits=7,
        decimal_places=2,
        null=True,
        blank=True,
    )
    percentage = models.DecimalField(
        max_digits=5,
        decimal_places=2,
        default=Decimal("0"),
    )
    duties_description = models.TextField(blank=True)
    sort_order = models.PositiveSmallIntegerField(default=0)

    class Meta:
        ordering = ["sort_order", "activity_name_snapshot"]
        verbose_name = "Period Report Line"
        verbose_name_plural = "Period Report Lines"

    def __str__(self):
        hours = f"{self.total_hours}h" if self.total_hours is not None else f"{self.percentage}%"
        return f"{self.activity_name_snapshot} — {hours}"


# =============================================================================
# PDF SNAPSHOTS
# =============================================================================


class PDFSnapshot(models.Model):
    class PDFType(models.TextChoices):
        WEEKLY = "WEEKLY", "Weekly Report"
        FINAL = "FINAL", "Final Period Report"

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
    pdf_type = models.CharField(max_length=6, choices=PDFType.choices)
    file = models.FileField(upload_to="timeeffort/pdfs/%Y/%m/")
    version = models.PositiveIntegerField(default=1)
    generated_at = models.DateTimeField(auto_now_add=True)
    generated_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        related_name="generated_pdfs",
    )
    checksum = models.CharField(max_length=64, help_text="SHA-256 of the PDF file content.")

    class Meta:
        ordering = ["-generated_at"]
        verbose_name = "PDF Snapshot"
        verbose_name_plural = "PDF Snapshots"

    def __str__(self):
        return f"{self.get_pdf_type_display()} v{self.version} — {self.generated_at:%Y-%m-%d}"


# =============================================================================
# DIRECTOR DEFAULT ALLOCATION
# =============================================================================


class DirectorDefaultAllocation(models.Model):
    """Default percentages for a director, pre-filled on each new period report."""

    profile = models.OneToOneField(
        StaffTimesheetProfile,
        on_delete=models.CASCADE,
        related_name="director_defaults",
    )
    main_grant_code = models.CharField(max_length=50, blank=True, help_text="e.g. DMS-2425344")
    main_grant_pct = models.DecimalField(max_digits=5, decimal_places=2, default=Decimal("80.00"))

    extra_grant_code_1 = models.CharField(max_length=50, blank=True)
    extra_grant_pct_1 = models.DecimalField(max_digits=5, decimal_places=2, default=Decimal("0"))
    extra_grant_code_2 = models.CharField(max_length=50, blank=True)
    extra_grant_pct_2 = models.DecimalField(max_digits=5, decimal_places=2, default=Decimal("0"))
    extra_grant_code_3 = models.CharField(max_length=50, blank=True)
    extra_grant_pct_3 = models.DecimalField(max_digits=5, decimal_places=2, default=Decimal("0"))
    extra_grant_code_4 = models.CharField(max_length=50, blank=True)
    extra_grant_pct_4 = models.DecimalField(max_digits=5, decimal_places=2, default=Decimal("0"))

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


# =============================================================================
# SALARY INDIRECT ALLOCATION  (default weekly hours per indirect category)
# =============================================================================


class SalaryIndirectAllocation(models.Model):
    """
    Default weekly hours for each indirect/leave/unallowable category for a salary employee.
    Pre-fills the corresponding rows on every weekly entry form.
    Set once by admin; employee overrides per-week as needed.
    """

    profile = models.OneToOneField(
        StaffTimesheetProfile,
        on_delete=models.CASCADE,
        related_name="salary_indirect",
    )
    hours_administrative = models.DecimalField(max_digits=5, decimal_places=2, default=Decimal("0"))
    hours_other_activity = models.DecimalField(max_digits=5, decimal_places=2, default=Decimal("0"))
    hours_sick_personal = models.DecimalField(max_digits=5, decimal_places=2, default=Decimal("0"))
    hours_vacation = models.DecimalField(max_digits=5, decimal_places=2, default=Decimal("0"))
    hours_fundraising_pr = models.DecimalField(max_digits=5, decimal_places=2, default=Decimal("0"))
    hours_other_unallowable = models.DecimalField(max_digits=5, decimal_places=2, default=Decimal("0"))

    class Meta:
        verbose_name = "Salary Indirect Allocation"
        verbose_name_plural = "Salary Indirect Allocations"

    def __str__(self):
        return f"Salary Indirect Defaults — {self.profile}"

    def hours_for_activity(self, activity_name):
        mapping = {
            "Administrative": self.hours_administrative,
            "Other Activity": self.hours_other_activity,
            "Sick / Personal Day": self.hours_sick_personal,
            "Vacation": self.hours_vacation,
            "Fundraising / PR": self.hours_fundraising_pr,
            "Other Unallowable": self.hours_other_unallowable,
        }
        return mapping.get(activity_name, Decimal("0"))
