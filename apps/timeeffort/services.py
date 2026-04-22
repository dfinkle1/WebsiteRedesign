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
    DirectorPeriodSubmission,
    DirectorSubmissionLine,
    PDFSnapshot,
    PeriodReport,
    PeriodReportLine,
    WeeklyTimesheet,
    WeeklyTimesheetLine,
)


# =============================================================================
# ROLLUP / CALCULATION
# =============================================================================


def get_period_rollup(staff_profile, period):
    """
    Compute rolled-up hours per (activity_name, grant_code, classification) across
    all submitted weeks in the period.

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
        week__period=period,
        status=WeeklyTimesheet.Status.SUBMITTED,
    ).prefetch_related("lines__activity")

    # Aggregate: key = (activity_name, grant_code, classification)
    aggregated = {}
    for ts in timesheets:
        for line in ts.lines.all():
            key = (
                str(line.activity),
                line.grant_code or line.activity.default_grant_code,
                line.activity.classification,
                line.activity.sort_order,
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
# PERIOD REPORT CREATION
# =============================================================================


def initialize_period_report(staff_profile, period):
    """
    Create or retrieve a PeriodReport for the given staff/period.
    Computes the rollup and creates PeriodReportLines in DESCRIBING status.
    Caller must have verified all_weeks_submitted before calling.
    """
    report, created = PeriodReport.objects.get_or_create(
        staff=staff_profile,
        period=period,
        defaults={"status": PeriodReport.Status.PENDING},
    )

    rollup = get_period_rollup(staff_profile, period)
    total_hours = sum(r["total_hours"] for r in rollup)

    # Delete existing lines (re-initialization after admin unlock)
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

    # Snapshot employee/supervisor info at this moment
    report.total_hours = total_hours
    report.supervisor_name_snapshot = staff_profile.supervisor_name
    report.employee_title_snapshot = staff_profile.title
    report.employee_name_snapshot = staff_profile.user.get_full_name() or staff_profile.user.username
    report.status = PeriodReport.Status.DESCRIBING
    report.save()

    return report


# =============================================================================
# PDF GENERATION
# =============================================================================


def _render_pdf_bytes(template_name, context):
    """Render a WeasyPrint PDF and return raw bytes."""
    try:
        from weasyprint import HTML
    except ImportError:
        raise RuntimeError("WeasyPrint is required for PDF generation. Install it with: pip install weasyprint")

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
    Generate the final period PDF. PeriodReport must be in DESCRIBING or GENERATED status
    with PeriodReportLines already saved (duties descriptions filled in).
    """
    lines = period_report.lines.order_by("sort_order", "activity_name_snapshot").all()

    # Group lines by classification for template rendering
    direct = [l for l in lines if l.classification_snapshot == Activity.Classification.DIRECT]
    indirect = [l for l in lines if l.classification_snapshot == Activity.Classification.INDIRECT]
    leave = [l for l in lines if l.classification_snapshot == Activity.Classification.LEAVE]
    unallowable = [l for l in lines if l.classification_snapshot == Activity.Classification.UNALLOWABLE]

    context = {
        "report": period_report,
        "staff": period_report.staff,
        "period": period_report.period,
        "direct_lines": direct,
        "indirect_lines": indirect,
        "leave_lines": leave,
        "unallowable_lines": unallowable,
        "total_hours": period_report.total_hours,
        "generated_at": timezone.now(),
    }

    pdf_bytes = _render_pdf_bytes("timeeffort/pdf/final_report.html", context)
    checksum = _sha256(pdf_bytes)

    existing = PDFSnapshot.objects.filter(
        period_report=period_report,
        pdf_type=PDFSnapshot.PDFType.FINAL,
    )
    version = _next_version(existing)

    filename = (
        f"final_{period_report.staff.user.username}"
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

    period_report.status = PeriodReport.Status.GENERATED
    period_report.generated_at = timezone.now()
    period_report.save(update_fields=["status", "generated_at"])

    return snapshot


def generate_final_pdf_async(period_report, generated_by=None):
    """Fire PDF generation in a background thread to avoid blocking the request."""
    t = threading.Thread(target=generate_final_pdf, args=(period_report, generated_by), daemon=True)
    t.start()


# =============================================================================
# DIRECTOR PDF
# =============================================================================


def count_holidays_in_period(period):
    """Return the number of AIM holidays that fall within the period's date range."""
    return AIMHoliday.objects.filter(date__range=[period.start_date, period.end_date]).count()


def generate_director_pdf(submission, generated_by=None):
    """
    Generate a director period effort PDF.
    Stores the file as a PDFSnapshot and returns it.
    """
    lines = submission.lines.order_by("slot", "category").all()
    direct_lines = [l for l in lines if l.category in (
        DirectorSubmissionLine.Category.DIRECT_MAIN,
        DirectorSubmissionLine.Category.DIRECT_EXTRA,
    )]
    indirect_lines = [l for l in lines if l.category not in (
        DirectorSubmissionLine.Category.DIRECT_MAIN,
        DirectorSubmissionLine.Category.DIRECT_EXTRA,
    )]
    total_pct = sum(l.percentage for l in lines)

    context = {
        "submission": submission,
        "staff": submission.staff,
        "period": submission.period,
        "direct_lines": direct_lines,
        "indirect_lines": indirect_lines,
        "total_pct": total_pct,
        "generated_at": timezone.now(),
    }

    pdf_bytes = _render_pdf_bytes("timeeffort/pdf/director_report.html", context)
    checksum = _sha256(pdf_bytes)

    existing = PDFSnapshot.objects.filter(
        director_submission=submission,
        pdf_type=PDFSnapshot.PDFType.DIRECTOR,
    )
    version = _next_version(existing)

    filename = (
        f"director_{submission.staff.user.username}"
        f"_{submission.period.start_date}_{submission.period.end_date}"
        f"_v{version}.pdf"
    )
    snapshot = PDFSnapshot(
        director_submission=submission,
        pdf_type=PDFSnapshot.PDFType.DIRECTOR,
        version=version,
        generated_by=generated_by,
        checksum=checksum,
    )
    snapshot.file.save(filename, ContentFile(pdf_bytes), save=True)
    return snapshot
