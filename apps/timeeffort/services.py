"""
Time & Effort Reporting — Service Layer

All business logic lives here: rollup calculations, PDF generation, validation.
Views should never compute percentages or touch WeasyPrint directly.
"""

import hashlib
import threading
from decimal import Decimal, ROUND_HALF_UP
from io import BytesIO

from django.core.files.base import ContentFile
from django.template.loader import render_to_string
from django.utils import timezone

from .models import (
    Activity,
    AIMHoliday,
    PDFSnapshot,
    PeriodReport,
    PeriodReportLine,
    WeeklyTimesheet,
    WeeklyTimesheetLine,
)


# =============================================================================
# ROLLUP / CALCULATION
# =============================================================================


def get_period_rollup(staff_profile, periods):
    """
    Compute rolled-up hours per (activity_name, grant_code, classification) across
    all submitted timesheets in the given periods.

    periods: a QuerySet or iterable of ReportingPeriod objects.
             For hourly staff this is one period; for salary staff, two.

    Returns a list of dicts:
        {
            "activity_name": str,
            "grant_code": str,
            "classification": str,
            "total_hours": Decimal,
            "percentage": Decimal,
            "sort_order": int,
        }
    Sorted by classification order then sort_order.
    """
    timesheets = WeeklyTimesheet.objects.filter(
        staff=staff_profile,
        week__period__in=periods,
        status=WeeklyTimesheet.Status.SUBMITTED,
    ).prefetch_related("lines__activity")

    # Aggregate: key = (activity_name, grant_code, classification, sort_order)
    aggregated = {}
    for ts in timesheets:
        for line in ts.lines.all():
            if line.activity_id:
                key = (
                    str(line.activity),
                    line.grant_code or line.activity.default_grant_code,
                    line.activity.classification,
                    line.activity.sort_order,
                )
            else:
                # Custom free-text row (salary only)
                key = (
                    line.custom_activity_name or "Custom Activity",
                    line.grant_code,
                    Activity.Classification.DIRECT,
                    999,
                )
            aggregated[key] = aggregated.get(key, Decimal("0")) + line.total_hours

    if not aggregated:
        return []

    total_hours = sum(aggregated.values())
    if total_hours == 0:
        return []

    classification_order = {
        Activity.Classification.DIRECT: 0,
        Activity.Classification.INDIRECT: 1,
        Activity.Classification.LEAVE: 2,
        Activity.Classification.UNALLOWABLE: 3,
    }

    rows = []
    for (activity_name, grant_code, classification, sort_order), hours in aggregated.items():
        percentage = (hours / total_hours * 100).quantize(Decimal("0.01"), rounding=ROUND_HALF_UP)
        rows.append(
            {
                "activity_name": activity_name,
                "grant_code": grant_code,
                "classification": classification,
                "total_hours": hours,
                "percentage": percentage,
                "sort_order": sort_order,
                "_class_order": classification_order.get(classification, 99),
            }
        )

    rows.sort(key=lambda r: (r["_class_order"], r["sort_order"], r["activity_name"]))
    return rows


def validate_period_percentages(rollup_rows):
    """
    Returns True if percentages sum to 100% ± 0.1 (rounding tolerance).
    """
    if not rollup_rows:
        return False
    total = sum(r["percentage"] for r in rollup_rows)
    return abs(total - Decimal("100")) <= Decimal("0.1")


# =============================================================================
# PERIOD REPORT CREATION / RE-INITIALIZATION
# =============================================================================


def initialize_period_report(report):
    """
    Create or refresh PeriodReportLines for a HOURS-based period report.

    Computes the rollup from all submitted WeeklyTimesheets across the report's
    covered periods (1 for hourly, 2 for salary), then writes PeriodReportLines.

    Snapshots employee/supervisor info at call time.
    Report is left in DRAFT status — caller must call report.submit() when ready.

    For PCT (director) reports use initialize_director_period_report() instead.
    """
    if report.submission_type != PeriodReport.SubmissionType.HOURS:
        raise ValueError("initialize_period_report() is for HOURS-based reports only.")

    rollup = get_period_rollup(report.staff, report.covered_periods)
    total_hours = sum(r["total_hours"] for r in rollup)

    # Replace all existing lines
    report.lines.all().delete()

    for i, row in enumerate(rollup):
        PeriodReportLine.objects.create(
            period_report=report,
            activity_name_snapshot=row["activity_name"],
            grant_code_snapshot=row["grant_code"],
            classification_snapshot=row["classification"],
            total_hours=row["total_hours"],
            percentage=row["percentage"],
            duties_description="",
            sort_order=i,
        )

    report.total_hours = total_hours
    report.supervisor_name_snapshot = report.staff.supervisor_name
    report.employee_title_snapshot = report.staff.title
    report.employee_name_snapshot = report.staff.user.get_full_name() or report.staff.user.username
    report.save(update_fields=[
        "total_hours",
        "supervisor_name_snapshot",
        "employee_title_snapshot",
        "employee_name_snapshot",
        "updated_at",
    ])

    return report


def initialize_director_period_report(report, defaults=None, holiday_pct=Decimal("0")):
    """
    Create or refresh PeriodReportLines for a PCT-based (director) period report
    using the director's DirectorDefaultAllocation as a starting template.

    defaults: DirectorDefaultAllocation instance (fetched from DB if None).
    holiday_pct: total holiday percentage (5% × holiday count) to subtract from
                 Administrative. The reduction is baked into the Administrative line
                 rather than stored as a separate Employer Holiday line.
    Lines are pre-populated with default percentages; director adjusts before submitting.
    Report is left in DRAFT status.
    """
    if report.submission_type != PeriodReport.SubmissionType.PCT:
        raise ValueError("initialize_director_period_report() is for PCT-based reports only.")

    if defaults is None:
        try:
            defaults = report.staff.director_defaults
        except Exception:
            defaults = None

    report.lines.all().delete()

    lines_to_create = []
    if defaults:
        sort = 0
        if defaults.main_grant_code or defaults.main_grant_pct:
            lines_to_create.append({
                "activity_name_snapshot": f"Direct — {defaults.main_grant_code or 'Main Grant'}",
                "grant_code_snapshot": defaults.main_grant_code,
                "classification_snapshot": Activity.Classification.DIRECT,
                "total_hours": None,
                "percentage": defaults.main_grant_pct,
                "sort_order": sort,
            })
            sort += 1
        for n in range(1, 5):
            code = getattr(defaults, f"extra_grant_code_{n}", "")
            pct = getattr(defaults, f"extra_grant_pct_{n}", Decimal("0"))
            if pct and pct > 0:
                lines_to_create.append({
                    "activity_name_snapshot": f"Direct — {code or f'Grant {n}'}",
                    "grant_code_snapshot": code,
                    "classification_snapshot": Activity.Classification.DIRECT,
                    "total_hours": None,
                    "percentage": pct,
                    "sort_order": sort,
                })
                sort += 1
        indirect_map = [
            ("Administrative", max(Decimal("0"), defaults.pct_administrative - holiday_pct)),
            ("Other Activity", defaults.pct_other_activity),
            ("Sick / Personal Day", defaults.pct_sick_personal),
            ("Vacation", defaults.pct_vacation),
            ("Fundraising / PR", defaults.pct_fundraising_pr),
            ("Other Unallowable", defaults.pct_other_unallowable),
        ]
        for label, pct in indirect_map:
            if pct and pct > 0:
                lines_to_create.append({
                    "activity_name_snapshot": label,
                    "grant_code_snapshot": "",
                    "classification_snapshot": Activity.Classification.INDIRECT,
                    "total_hours": None,
                    "percentage": pct,
                    "sort_order": sort,
                })
                sort += 1

    for data in lines_to_create:
        PeriodReportLine.objects.create(period_report=report, duties_description="", **data)

    report.supervisor_name_snapshot = report.staff.supervisor_name
    report.employee_title_snapshot = report.staff.title
    report.employee_name_snapshot = report.staff.user.get_full_name() or report.staff.user.username
    report.save(update_fields=[
        "supervisor_name_snapshot",
        "employee_title_snapshot",
        "employee_name_snapshot",
        "updated_at",
    ])

    return report


# =============================================================================
# PDF GENERATION
# =============================================================================


def _render_pdf_bytes(template_name, context):
    """Render a WeasyPrint PDF and return raw bytes."""
    try:
        from weasyprint import HTML
    except ImportError:
        raise RuntimeError(
            "WeasyPrint is required for PDF generation. Install it with: pip install weasyprint"
        )
    html_string = render_to_string(template_name, context)
    pdf_bytes = HTML(string=html_string, base_url="/").write_pdf()
    return pdf_bytes


def _sha256(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def _next_version(queryset):
    latest = queryset.order_by("-version").first()
    return (latest.version + 1) if latest else 1


def generate_weekly_pdf(timesheet, generated_by=None):
    """
    Generate a weekly PDF snapshot for a submitted timesheet.
    Stores the file and returns the PDFSnapshot instance.
    """
    lines = (
        timesheet.lines.select_related("activity")
        .order_by("activity__sort_order", "activity__name")
        .all()
    )

    context = {
        "timesheet": timesheet,
        "staff": timesheet.staff,
        "week": timesheet.week,
        "period": timesheet.week.period,
        "lines": lines,
        "total_hours": timesheet.total_hours,
        "day_labels": ["Sun", "Mon", "Tue", "Wed", "Thu", "Fri", "Sat"],
        "generated_at": timezone.now(),
    }

    pdf_bytes = _render_pdf_bytes("timeeffort/pdf/weekly_report.html", context)
    checksum = _sha256(pdf_bytes)

    existing = PDFSnapshot.objects.filter(
        timesheet=timesheet,
        pdf_type=PDFSnapshot.PDFType.WEEKLY,
    )
    version = _next_version(existing)

    filename = f"weekly_{timesheet.staff.user.username}_{timesheet.week.start_date}_v{version}.pdf"
    snapshot = PDFSnapshot(
        timesheet=timesheet,
        pdf_type=PDFSnapshot.PDFType.WEEKLY,
        version=version,
        generated_by=generated_by,
        checksum=checksum,
    )
    snapshot.file.save(filename, ContentFile(pdf_bytes), save=True)
    return snapshot


def generate_final_pdf(period_report, generated_by=None):
    """
    Generate the final period PDF for a HOURS or PCT report.

    HOURS reports (salary/hourly) → combined_report.html with 4 weekly grids + rollup.
    PCT reports (director)        → final_report.html with percentage table.

    PeriodReportLines must already be saved with duties descriptions filled in.
    Sets generated_at on the report. Returns the PDFSnapshot instance.
    """
    if period_report.submission_type == PeriodReport.SubmissionType.HOURS:
        return _generate_combined_hours_pdf(period_report, generated_by)
    return _generate_pct_pdf(period_report, generated_by)


def _generate_pct_pdf(period_report, generated_by=None):
    """Director PCT-based PDF using the existing final_report template."""
    lines = period_report.lines.order_by("sort_order", "activity_name_snapshot").all()
    direct = [ln for ln in lines if ln.classification_snapshot == Activity.Classification.DIRECT]
    indirect = [ln for ln in lines if ln.classification_snapshot == Activity.Classification.INDIRECT]
    leave = [ln for ln in lines if ln.classification_snapshot == Activity.Classification.LEAVE]
    unallowable = [ln for ln in lines if ln.classification_snapshot == Activity.Classification.UNALLOWABLE]

    context = {
        "report": period_report,
        "staff": period_report.staff,
        "period": period_report.period,
        "direct_lines": direct,
        "indirect_lines": indirect,
        "leave_lines": leave,
        "unallowable_lines": unallowable,
        "total_hours": period_report.total_hours,
        "is_pct_report": True,
        "generated_at": timezone.now(),
    }
    return _save_final_snapshot(period_report, generated_by, "timeeffort/pdf/final_report.html", context, "final")


def _generate_combined_hours_pdf(period_report, generated_by=None):
    """Salary/hourly HOURS-based PDF: cover + 4 weekly grids + rollup table."""
    from .models import ReportingWeek

    lines = period_report.lines.order_by("sort_order", "activity_name_snapshot").all()
    direct = [ln for ln in lines if ln.classification_snapshot == Activity.Classification.DIRECT]
    indirect = [ln for ln in lines if ln.classification_snapshot == Activity.Classification.INDIRECT]
    leave = [ln for ln in lines if ln.classification_snapshot == Activity.Classification.LEAVE]
    unallowable = [ln for ln in lines if ln.classification_snapshot == Activity.Classification.UNALLOWABLE]

    covered_weeks = ReportingWeek.objects.filter(
        period__in=period_report.covered_periods
    ).order_by("start_date")

    weekly_data = []
    for week in covered_weeks:
        ts = (
            WeeklyTimesheet.objects.filter(staff=period_report.staff, week=week)
            .prefetch_related("lines__activity")
            .first()
        )
        nonzero_lines = [ln for ln in ts.lines.all() if ln.total_hours > 0] if ts else []
        weekly_data.append({
            "week": week,
            "timesheet": ts,
            "lines": nonzero_lines,
            "total": ts.total_hours if ts else Decimal("0"),
        })

    context = {
        "report": period_report,
        "staff": period_report.staff,
        "period": period_report.period,
        "direct_lines": direct,
        "indirect_lines": indirect,
        "leave_lines": leave,
        "unallowable_lines": unallowable,
        "weekly_data": weekly_data,
        "total_hours": period_report.total_hours,
        "is_pct_report": False,
        "generated_at": timezone.now(),
        "day_labels": ["Sun", "Mon", "Tue", "Wed", "Thu", "Fri", "Sat"],
    }
    return _save_final_snapshot(period_report, generated_by, "timeeffort/pdf/combined_report.html", context, "combined")


def _save_final_snapshot(period_report, generated_by, template_name, context, prefix):
    pdf_bytes = _render_pdf_bytes(template_name, context)
    checksum = _sha256(pdf_bytes)

    existing = PDFSnapshot.objects.filter(
        period_report=period_report,
        pdf_type=PDFSnapshot.PDFType.FINAL,
    )
    version = _next_version(existing)

    filename = (
        f"{prefix}_{period_report.staff.user.username}"
        f"_{period_report.period.start_date}_{period_report.period.end_date}"
        f"_v{version}.pdf"
    )
    snapshot = PDFSnapshot(
        period_report=period_report,
        pdf_type=PDFSnapshot.PDFType.FINAL,
        version=version,
        generated_by=generated_by,
        checksum=checksum,
    )
    snapshot.file.save(filename, ContentFile(pdf_bytes), save=True)

    period_report.generated_at = timezone.now()
    period_report.save(update_fields=["generated_at", "updated_at"])

    return snapshot


def generate_final_pdf_async(period_report, generated_by=None):
    """Fire PDF generation in a background thread to avoid blocking the request."""
    t = threading.Thread(target=generate_final_pdf, args=(period_report, generated_by), daemon=True)
    t.start()


# =============================================================================
# HOLIDAY UTILITIES
# =============================================================================


def count_holidays_in_period(period):
    """Return the number of AIM holidays that fall within the period's date range."""
    return AIMHoliday.objects.filter(date__range=[period.start_date, period.end_date]).count()
